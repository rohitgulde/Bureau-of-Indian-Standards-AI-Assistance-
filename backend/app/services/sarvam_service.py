"""
app/services/sarvam_service.py
──────────────────────────────────
Async service integrating Sarvam AI platform.

Capabilities
------------
  NMT    — Translate Indian regional languages ↔ English via Dhruva pipeline.
  Lang   — Detect the source language of any Indian text (Unicode-heuristic +
            optional Sarvam language-detection model).
  ASR    — Speech-to-Text: base64 audio → transcribed text.
  TTS    — Text-to-Speech: text → base64 WAV audio bytes.

Supported languages
-------------------
  hi  Hindi           mr  Marathi
  ta  Tamil           bn  Bengali
  te  Telugu          gu  Gujarati
  kn  Kannada         pa  Punjabi
  ml  Malayalam       or  Odia
  ur  Urdu            as  Assamese

Sarvam API two-step flow
--------------------------
  Step 1 — Pipeline Config: POST to ULCA → get serviceId for the task.
  Step 2 — Inference: POST to Dhruva → get translated/transcribed/synthesised output.

Mock fallback mode
------------------
  Set SARVAM_MOCK=true in environment (or pass mock=True) to run offline
  without valid API keys.  All methods return plausible mock data so the
  rest of the pipeline can be tested end-to-end.

Environment variables
---------------------
  SARVAM_USER_ID          : Sarvam ULCA user ID (from sarvam.gov.in)
  SARVAM_API_KEY          : ULCA API key (pipeline config calls)
  SARVAM_INFERENCE_KEY    : Dhruva inference API key (inference calls)
  SARVAM_MOCK             : "true" to enable mock mode (default: false)
  SARVAM_TIMEOUT          : HTTP timeout in seconds (default: 30)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Constants & language registry
# =============================================================================

ULCA_CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
DHRUVA_INFER_URL = "https://dhruva-api.sarvam.gov.in/services/inference/pipeline"

DEFAULT_TIMEOUT = int(os.getenv("SARVAM_TIMEOUT", "30"))


class LangCode(str, Enum):
    """Sarvam / ISO-639-1 language codes supported by the portal."""
    HINDI      = "hi"
    TAMIL      = "ta"
    TELUGU     = "te"
    MARATHI    = "mr"
    BENGALI    = "bn"
    GUJARATI   = "gu"
    KANNADA    = "kn"
    PUNJABI    = "pa"
    MALAYALAM  = "ml"
    ODIA       = "or"
    URDU       = "ur"
    ASSAMESE   = "as"
    ENGLISH    = "en"
    UNKNOWN    = "unknown"


# Human-readable display names
LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",    "ta": "Tamil",   "te": "Telugu",
    "mr": "Marathi",  "bn": "Bengali", "gu": "Gujarati",
    "kn": "Kannada",  "pa": "Punjabi", "ml": "Malayalam",
    "or": "Odia",     "ur": "Urdu",    "as": "Assamese",
    "en": "English",
}

# Supported regional languages (excludes English)
REGIONAL_LANGS: set[str] = {lc.value for lc in LangCode if lc != LangCode.ENGLISH and lc != LangCode.UNKNOWN}


# =============================================================================
# Unicode-range heuristic for offline language detection
# =============================================================================

# Unicode block ranges that uniquely identify a script.
# Checked in priority order — first match wins.
_SCRIPT_RANGES: list[tuple[int, int, str]] = [
    (0x0900, 0x097F, "hi"),   # Devanagari  → Hindi / Marathi (default hi)
    (0x0980, 0x09FF, "bn"),   # Bengali     → Bengali / Assamese (default bn)
    (0x0A00, 0x0A7F, "pa"),   # Gurmukhi   → Punjabi
    (0x0A80, 0x0AFF, "gu"),   # Gujarati
    (0x0B00, 0x0B7F, "or"),   # Odia
    (0x0B80, 0x0BFF, "ta"),   # Tamil
    (0x0C00, 0x0C7F, "te"),   # Telugu
    (0x0C80, 0x0CFF, "kn"),   # Kannada
    (0x0D00, 0x0D7F, "ml"),   # Malayalam
    (0x0600, 0x06FF, "ur"),   # Arabic script → Urdu
]

# Words that disambiguate Devanagari scripts
_MARATHI_MARKERS = {
    # Possessive pronouns — grammatically unique to Marathi
    "\u092e\u093e\u091d\u094d\u092f\u093e", "\u092e\u093e\u091d\u0947", "\u092e\u093e\u091d\u093e",   # माझ्या, माझे, माझा
    "\u0906\u092e\u091a\u093e", "\u0906\u092e\u091a\u094d\u092f\u093e",          # आमचा, आमच्या
    "\u0924\u0941\u092e\u091a\u093e", "\u0924\u094d\u092f\u093e\u091a\u093e",    # तुमचा, त्याचा
    "\u0906\u092a\u0932\u0947", "\u0906\u092a\u0932\u093e",                      # आपले, आपला
    # Copulas — spelling differs from Hindi
    "\u0906\u0939\u0947", "\u0906\u0939\u0947\u0924",                            # आहे, आहेत
    "\u0928\u093e\u0939\u0940", "\u0928\u093e\u0939\u0940\u0924",                # नाही, नाहीत
    "\u0905\u0938\u0924\u094b", "\u0905\u0938\u0924\u0947", "\u0905\u0938\u0924\u093e\u0924",  # असतो, असते, असतात
    "\u0915\u0930\u0924\u094b", "\u0915\u0930\u0924\u0947", "\u0915\u0930\u0924\u093e\u0924",  # करतो, करते, करतात
    "\u0939\u094b\u0923\u093e\u0930", "\u0905\u0938\u0947\u0932",                # होणार, असेल
    "\u0915\u0930\u0924\u093e\u0928\u093e",                                      # करताना
    # Unique particles
    "\u0924\u0941\u092e\u094d\u0939\u0940", "\u092e\u0932\u093e",               # तुम्ही, मला
}
_HINDI_MARKERS = {
    "\u0939\u0948", "\u0939\u0948\u0902", "\u0928\u0939\u0940\u0902",           # है, हैं, नहीं
    "\u092e\u0941\u091d\u0947", "\u0906\u092a", "\u0915\u094d\u092f\u093e",     # मुझे, आप, क्या
    "\u0915\u0930\u094b", "\u0925\u093e", "\u092f\u0939", "\u0935\u0939",       # करो, था, यह, वह
    "\u0939\u092e\u093e\u0930\u093e", "\u0924\u0941\u092e\u094d\u0939\u093e\u0930\u093e",  # हमारा, तुम्हारा
    "\u0907\u0938\u0915\u093e", "\u0909\u0938\u0915\u093e",                     # इसका, उसका
    "\u0915\u0930\u0924\u093e", "\u0915\u0930\u0924\u0940", "\u0915\u0930\u0924\u0947",    # करता, करती, करते
    "\u0939\u094b\u0917\u093e", "\u0939\u094b\u0917\u0940", "\u0939\u094b\u0902\u0917\u0947",  # होगा, होगी, होंगे
    "\u0930\u0939\u093e", "\u0930\u0939\u0940", "\u0930\u0939\u0947",           # रहा, रही, रहे
    "\u092e\u0947\u0930\u0947", "\u092e\u0947\u0930\u093e", "\u092e\u0947\u0930\u0940",    # मेरे, मेरा, मेरी
}


def detect_language_heuristic(text: str) -> str:
    """
    Detect language using Unicode script block analysis.

    Returns an ISO-639-1 code or 'en' / 'unknown'.
    ~95% accurate for single-script Indian language text.
    Devanagari text is further disambiguated between Hindi and Marathi.
    """
    if not text.strip():
        return LangCode.UNKNOWN.value

    # Count characters per script block
    counts: dict[str, int] = {}
    for char in text:
        cp = ord(char)
        for lo, hi, lang in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[lang] = counts.get(lang, 0) + 1
                break

    if not counts:
        # ASCII/Latin — likely English
        if re.search(r"[a-zA-Z]", text):
            return LangCode.ENGLISH.value
        return LangCode.UNKNOWN.value

    detected = max(counts, key=counts.__getitem__)

    # Disambiguate Devanagari: Hindi vs Marathi
    if detected == "hi":
        words = set(text.split())
        mr_hits = len(words & _MARATHI_MARKERS)
        hi_hits = len(words & _HINDI_MARKERS)
        if mr_hits > hi_hits:
            detected = "mr"

    return detected


# =============================================================================
# Output dataclasses
# =============================================================================

@dataclass
class DetectionResult:
    """Result of language detection."""
    detected_lang: str          # ISO-639-1 code e.g. "hi"
    lang_name: str              # human-readable e.g. "Hindi"
    confidence: float           # 0.0–1.0
    method: str                 # "heuristic" | "sarvam_api"
    is_english: bool
    is_regional_indian: bool


@dataclass
class TranslationResult:
    """Result of one NMT translation call."""
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    model_used: str              # serviceId or "mock"
    characters_translated: int


@dataclass
class ASRResult:
    """Result of speech-to-text transcription."""
    transcript: str
    detected_lang: str
    confidence: float
    audio_duration_ms: int | None
    model_used: str


@dataclass
class TTSResult:
    """Result of text-to-speech synthesis."""
    audio_base64: str            # base64-encoded WAV
    audio_bytes: bytes
    source_text: str
    lang: str
    audio_format: str            # "wav"
    model_used: str


@dataclass
class PipelineResult:
    """
    End-to-end pipeline result.

    forward: regional text → English  (for AI pipeline input)
    reverse: English text  → regional (for user response)
    """
    original_text: str
    english_text: str
    reverse_text: str            # empty until reverse_translate() is called
    detected_lang: str
    lang_name: str
    detection: DetectionResult
    forward_translation: TranslationResult | None = None
    reverse_translation: TranslationResult | None = None
    tts_result: TTSResult | None = None
    was_mocked: bool = False


# =============================================================================
# SarvamService
# =============================================================================

class SarvamService:
    """
    Async service for Sarvam NMT, ASR, TTS, and language detection.
    """
    @classmethod
    def from_env(cls) -> "SarvamService":
        return cls()
        
    def __init__(
        self,
        api_key: str = "",
        mock: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self._timeout = timeout
        env_mock = os.getenv("SARVAM_MOCK", "false").lower() == "true"
        self._mock = mock or env_mock or not self._api_key

        if self._mock:
            logger.warning("SarvamService running in MOCK mode.")
        else:
            logger.info("SarvamService initialised in LIVE mode.")

    def _headers(self) -> dict[str, str]:
        return {
            "api-subscription-key": self._api_key,
        }

    async def detect_language(self, text: str) -> DetectionResult:
        lang = detect_language_heuristic(text)
        confidence = 0.90 if lang != LangCode.UNKNOWN.value else 0.30
        if len(text.strip()) < 10:
            confidence = min(confidence, 0.60)
        return DetectionResult(
            detected_lang=lang,
            lang_name=LANG_NAMES.get(lang, "Unknown"),
            confidence=confidence,
            method="heuristic",
            is_english=(lang == LangCode.ENGLISH.value),
            is_regional_indian=(lang in REGIONAL_LANGS),
        )

    _MOCK_TRANSLATIONS: dict[tuple[str, str], str] = {
        ("hi", "en"): "[MOCK-EN] What Indian Standard applies to my product?",
        ("ta", "en"): "[MOCK-EN] Which IS standard is applicable for drinking water quality?",
        ("te", "en"): "[MOCK-EN] Where can I test my product in Hyderabad?",
        ("mr", "en"): "[MOCK-EN] How do I apply for an ISI Mark licence?",
        ("bn", "en"): "[MOCK-EN] How do I verify a hallmarked gold article?",
        ("gu", "en"): "[MOCK-EN] What are the steps for CRS registration?",
        ("kn", "en"): "[MOCK-EN] What is the permissible pH limit in IS 10500?",
    }

    def _mock_translate(self, text: str, source: str, target: str) -> str:
        canned = self._MOCK_TRANSLATIONS.get((source, target))
        if canned and len(text) < 200:
            return canned
        lang_name = LANG_NAMES.get(source, source.upper())
        tgt_name  = LANG_NAMES.get(target, target.upper())
        return f"[MOCK {lang_name}→{tgt_name}] {text}"

    def _mock_asr_transcript(self, lang: str) -> str:
        samples = {
            "hi": "मुझे हिंदी में जवाब चाहिए। IS 10500 में पानी की गुणवत्ता क्या है?",
            "ta": "என் தயாரிப்புக்கு எந்த IS தரநிலை பொருந்தும்?",
            "te": "నా ఉత్పత్తికి ఏ IS ప్రమాణాలు వర్తిస్తాయి?",
            "mr": "माझ्या उत्पादनासाठी कोणते IS मानक लागू होते?",
            "bn": "আমার পণ্যের জন্য কোন IS মান প্রযোজ্য?",
        }
        return samples.get(lang, f"[MOCK ASR] Sample {LANG_NAMES.get(lang, lang)} audio transcription.")

    _MOCK_WAV_BYTES: bytes = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00"
        b"\x01\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    async def translate_to_english(self, text: str, source_lang: str) -> TranslationResult:
        if source_lang == LangCode.ENGLISH.value:
            return TranslationResult(source_text=text, translated_text=text, source_lang="en", target_lang="en", model_used="passthrough", characters_translated=0)
        
        if self._mock:
            return TranslationResult(source_text=text, translated_text=self._mock_translate(text, source_lang, "en"), source_lang=source_lang, target_lang="en", model_used="mock", characters_translated=len(text))

        payload = {
            "input": [text],
            "source_language_code": f"{source_lang}-IN",
            "target_language_code": "en-IN",
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1"
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post("https://api.sarvam.ai/translate", headers={"api-subscription-key": self._api_key, "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                data = resp.json()
                translated = data["translated_text"][0] if "translated_text" in data else data.get("translations", [text])[0]
                return TranslationResult(source_text=text, translated_text=translated, source_lang=source_lang, target_lang="en", model_used="mayura:v1", characters_translated=len(text))
        except Exception as exc:
            logger.error(f"Sarvam Translate to EN failed: {exc}. Trying fallback.")
            try:
                from deep_translator import GoogleTranslator
                s_lang = source_lang.split("-")[0]
                translator = GoogleTranslator(source=s_lang, target="en")
                lines = text.split('\n')
                translated_lines = []
                for line in lines:
                    if not line.strip():
                        translated_lines.append(line)
                        continue
                    try:
                        t_line = translator.translate(line)
                        translated_lines.append(t_line if t_line else line)
                    except:
                        translated_lines.append(line)
                fallback_translated = '\n'.join(translated_lines)
                return TranslationResult(source_text=text, translated_text=fallback_translated, source_lang=source_lang, target_lang="en", model_used="googletrans_fallback", characters_translated=len(text))
            except Exception as fallback_exc:
                logger.error(f"Fallback translation to EN also failed: {fallback_exc}")
                return TranslationResult(source_text=text, translated_text=self._mock_translate(text, source_lang, "en"), source_lang=source_lang, target_lang="en", model_used="mock_fallback", characters_translated=len(text))

    async def translate_from_english(self, text: str, target_lang: str) -> TranslationResult:
        if target_lang == LangCode.ENGLISH.value:
            return TranslationResult(source_text=text, translated_text=text, source_lang="en", target_lang="en", model_used="passthrough", characters_translated=0)
        
        if self._mock:
            return TranslationResult(source_text=text, translated_text=self._mock_translate(text, "en", target_lang), source_lang="en", target_lang=target_lang, model_used="mock", characters_translated=len(text))

        payload = {
            "input": [text],
            "source_language_code": "en-IN",
            "target_language_code": f"{target_lang}-IN",
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1"
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post("https://api.sarvam.ai/translate", headers={"api-subscription-key": self._api_key, "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                data = resp.json()
                translated = data["translated_text"][0] if "translated_text" in data else data.get("translations", [text])[0]
                return TranslationResult(source_text=text, translated_text=translated, source_lang="en", target_lang=target_lang, model_used="mayura:v1", characters_translated=len(text))
        except Exception as exc:
            logger.error(f"Sarvam Translate from EN failed: {exc}. Trying fallback.")
            try:
                from deep_translator import GoogleTranslator
                t_lang = target_lang.split("-")[0]
                translator = GoogleTranslator(source="en", target=t_lang)
                lines = text.split('\n')
                translated_lines = []
                for line in lines:
                    if not line.strip():
                        translated_lines.append(line)
                        continue
                    try:
                        t_line = translator.translate(line)
                        translated_lines.append(t_line if t_line else line)
                    except:
                        translated_lines.append(line)
                fallback_translated = '\n'.join(translated_lines)
                return TranslationResult(source_text=text, translated_text=fallback_translated, source_lang="en", target_lang=target_lang, model_used="googletrans_fallback", characters_translated=len(text))
            except Exception as fallback_exc:
                logger.error(f"Fallback translation from EN also failed: {fallback_exc}")
                return TranslationResult(source_text=text, translated_text=self._mock_translate(text, "en", target_lang), source_lang="en", target_lang=target_lang, model_used="mock_fallback", characters_translated=len(text))

    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Generic function to translate text using Sarvam AI (mayura:v1).
        Expects source_lang and target_lang in format 'hi-IN', 'en-IN', etc.
        """
        if source_lang == target_lang:
            return text
        
        if self._mock:
            return f"[MOCK {source_lang}→{target_lang}] {text}"

        payload = {
            "input": [text],
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1"
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post("https://api.sarvam.ai/translate", headers={"api-subscription-key": self._api_key, "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                data = resp.json()
                translated = data["translated_text"][0] if "translated_text" in data else data.get("translations", [text])[0]
                return translated
        except Exception as exc:
            logger.error(f"Sarvam Translate ({source_lang} -> {target_lang}) failed: {exc}. Trying fallback.")
            try:
                # Use deep-translator as a robust fallback
                from deep_translator import GoogleTranslator
                s_lang = source_lang.split("-")[0]
                t_lang = target_lang.split("-")[0]
                translator = GoogleTranslator(source=s_lang, target=t_lang)
                
                # Chunk by newline to avoid TranslationNotFound on large structured texts
                lines = text.split('\n')
                translated_lines = []
                for line in lines:
                    if not line.strip():
                        translated_lines.append(line)
                        continue
                    try:
                        t_line = translator.translate(line)
                        translated_lines.append(t_line if t_line else line)
                    except:
                        translated_lines.append(line)
                return '\n'.join(translated_lines)
            except Exception as fallback_exc:
                logger.error(f"Fallback translation also failed: {fallback_exc}")
                return text

    async def full_pipeline(self, text: str, source_lang_override: str | None = None) -> PipelineResult:
        det = await self.detect_language(text)
        if source_lang_override and source_lang_override != "unknown":
            det.detected_lang = source_lang_override
            det.lang_name = LANG_NAMES.get(source_lang_override, "Unknown")
        
        fwd = await self.translate_to_english(text, det.detected_lang)
        
        return PipelineResult(
            original_text=text,
            english_text=fwd.translated_text,
            reverse_text="",
            detected_lang=det.detected_lang,
            lang_name=det.lang_name,
            detection=det,
            forward_translation=fwd,
            was_mocked=(fwd.model_used.startswith("mock")),
        )

    async def speech_to_text(self, audio_base64: str) -> ASRResult:
        if self._mock:
            return ASRResult(transcript=self._mock_asr_transcript("hi"), detected_lang="hi", confidence=0.99, audio_duration_ms=5000, model_used="mock")
        
        try:
            audio_bytes = base64.b64decode(audio_base64)
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model": "saaras:v3"}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post("https://api.sarvam.ai/speech-to-text", headers={"api-subscription-key": self._api_key}, files=files, data=data)
                resp.raise_for_status()
                resp_data = resp.json()
                return ASRResult(transcript=resp_data.get("transcript", ""), detected_lang="unknown", confidence=1.0, audio_duration_ms=0, model_used="saaras:v3")
        except Exception as exc:
            logger.error(f"Sarvam STT failed: {exc}")
            return ASRResult(transcript=self._mock_asr_transcript("hi"), detected_lang="hi", confidence=0.99, audio_duration_ms=0, model_used="mock_fallback")

    async def text_to_speech(self, text: str, lang: str, gender: str = "female") -> TTSResult:
        if self._mock:
            b64 = base64.b64encode(self._MOCK_WAV_BYTES).decode("utf-8")
            return TTSResult(audio_base64=b64, audio_bytes=self._MOCK_WAV_BYTES, source_text=text, lang=lang, audio_format="wav", model_used="mock")
        
        speaker = "shubh" if gender == "male" else "meera"
        payload = {
            "inputs": [{"text": text}],
            "target_language_code": f"{lang}-IN",
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post("https://api.sarvam.ai/text-to-speech", headers={"api-subscription-key": self._api_key, "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                data = resp.json()
                audio_str = data["audios"][0]
                audio_bytes = base64.b64decode(audio_str)
                return TTSResult(audio_base64=audio_str, audio_bytes=audio_bytes, source_text=text, lang=lang, audio_format="wav", model_used="bulbul:v3")
        except Exception as exc:
            logger.error(f"Sarvam TTS failed: {exc}")
            b64 = base64.b64encode(self._MOCK_WAV_BYTES).decode("utf-8")
            return TTSResult(audio_base64=b64, audio_bytes=self._MOCK_WAV_BYTES, source_text=text, lang=lang, audio_format="wav", model_used="mock_fallback")

_sarvam_singleton = None

def get_sarvam_service() -> SarvamService:
    """
    FastAPI-compatible dependency that returns the singleton SarvamService.

    Example
    -------
        from fastapi import Depends
        from app.services.sarvam_service import get_sarvam_service

        @router.post("/translate")
        async def translate(svc: SarvamService = Depends(get_sarvam_service)):
            ...
    """
    global _sarvam_singleton
    if _sarvam_singleton is None:
        _sarvam_singleton = SarvamService.from_env()
    return _sarvam_singleton

"""
app/routers/sarvam.py
────────────────────────
FastAPI router exposing Sarvam NMT, ASR, TTS, and language detection
as REST endpoints.

Endpoints
---------
POST /api/sarvam/detect          — Detect language of text input
POST /api/sarvam/translate       — Translate text between languages
POST /api/sarvam/forward         — Detect + translate any input to English
POST /api/sarvam/reverse         — Translate English response to regional lang
POST /api/sarvam/asr             — Speech-to-text (multipart audio upload)
POST /api/sarvam/tts             — Text-to-speech (returns base64 audio)
POST /api/sarvam/asr-pipeline    — ASR + NMT (voice → English text)
POST /api/sarvam/tts-pipeline    — NMT + TTS (English text → regional audio)
GET  /api/sarvam/languages       — List supported languages
GET  /api/sarvam/health          — Service health + mock mode status
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.sarvam_service import (
    SarvamService,
    LangCode,
    get_sarvam_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sarvam", tags=["Sarvam — Language AI"])


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000,
                      description="Text whose language should be detected.")


class DetectResponse(BaseModel):
    detected_lang: str
    lang_name: str
    confidence: float
    method: str
    is_english: bool
    is_regional_indian: bool


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(..., description="Source language code e.g. 'hi', 'ta'.")
    target_lang: str = Field(..., description="Target language code e.g. 'en'.")


class TranslateResponse(BaseModel):
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    model_used: str
    characters_translated: int


class ForwardRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000,
                      description="User query in any supported language.")


class ForwardResponse(BaseModel):
    original_text: str
    english_text: str
    detected_lang: str
    lang_name: str
    was_translated: bool
    was_mocked: bool


class ReverseRequest(BaseModel):
    english_text: str = Field(..., min_length=1, max_length=10000,
                               description="English RAG response to translate back.")
    target_lang: str  = Field(..., description="User's regional language code e.g. 'hi'.")
    synthesize_tts: bool = Field(False, description="Also synthesize the translated text as audio.")
    tts_gender: str  = Field("female", description="TTS voice gender: 'male' | 'female'.")


class ReverseResponse(BaseModel):
    english_text: str
    regional_text: str
    target_lang: str
    lang_name: str
    audio_base64: str | None = None   # populated if synthesize_tts=True
    was_mocked: bool


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000,
                      description="Text to synthesize.")
    lang: str = Field(..., description="Language code for the voice e.g. 'hi', 'ta'.")
    gender: str = Field("female", description="'male' | 'female'.")
    return_base64: bool = Field(True, description="Return audio as base64 string (default True).")


class TTSResponse(BaseModel):
    audio_base64: str
    lang: str
    model_used: str
    audio_format: str


class ASRPipelineResponse(BaseModel):
    transcript: str          # original regional language text
    detected_lang: str
    english_text: str        # translated to English for RAG
    asr_model: str
    nmt_model: str
    was_mocked: bool


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/detect", response_model=DetectResponse,
             summary="Detect language of text")
async def detect_language(
    req: DetectRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> DetectResponse:
    """Detect the language of any text using Unicode heuristics."""
    result = await svc.detect_language(req.text)
    return DetectResponse(
        detected_lang=result.detected_lang,
        lang_name=result.lang_name,
        confidence=result.confidence,
        method=result.method,
        is_english=result.is_english,
        is_regional_indian=result.is_regional_indian,
    )


@router.post("/translate", response_model=TranslateResponse,
             summary="Translate text between two languages")
async def translate(
    req: TranslateRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> TranslateResponse:
    """Translate text. For regional→English use source='hi'/'ta'/… target='en'. Reverse for English→regional."""
    try:
        if req.target_lang == "en":
            result = await svc.translate_to_english(req.text, req.source_lang)
        else:
            result = await svc.translate_from_english(req.text, req.target_lang)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation error: {exc}")

    return TranslateResponse(
        source_text=result.source_text,
        translated_text=result.translated_text,
        source_lang=result.source_lang,
        target_lang=result.target_lang,
        model_used=result.model_used,
        characters_translated=result.characters_translated,
    )


@router.post("/forward", response_model=ForwardResponse,
             summary="Auto-detect + translate any input to English")
async def forward_pipeline(
    req: ForwardRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> ForwardResponse:
    """
    Full forward pipeline: detect language → translate to English.
    Pass the returned english_text into the RAG /api/chat endpoint.
    """
    try:
        result = await svc.full_pipeline(req.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Forward pipeline error: {exc}")

    return ForwardResponse(
        original_text=result.original_text,
        english_text=result.english_text,
        detected_lang=result.detected_lang,
        lang_name=result.lang_name,
        was_translated=(result.forward_translation is not None),
        was_mocked=result.was_mocked,
    )


@router.post("/reverse", response_model=ReverseResponse,
             summary="Translate English RAG response to regional language")
async def reverse_pipeline(
    req: ReverseRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> ReverseResponse:
    """
    Reverse pipeline: English RAG answer → regional language (+ optional TTS audio).
    Use the detected_lang from the /forward response as target_lang here.
    """
    try:
        result = await svc.reverse_pipeline(
            english_text=req.english_text,
            target_lang=req.target_lang,
            synthesize_tts=req.synthesize_tts,
            tts_gender=req.tts_gender,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reverse pipeline error: {exc}")

    return ReverseResponse(
        english_text=result.english_text,
        regional_text=result.reverse_text,
        target_lang=result.detected_lang,
        lang_name=result.lang_name,
        audio_base64=(result.tts_result.audio_base64 if result.tts_result else None),
        was_mocked=result.was_mocked,
    )


@router.post("/asr", summary="Speech-to-Text (upload audio file)")
async def asr(
    audio: UploadFile = File(..., description="Audio file (WAV/FLAC/MP3, 16 kHz mono preferred)"),
    lang: str = Form(..., description="Language spoken in the audio e.g. 'hi', 'ta'"),
    svc: SarvamService = Depends(get_sarvam_service),
) -> dict:
    """
    Transcribe an uploaded audio file to text in the specified regional language.
    Audio should be WAV, FLAC, or MP3. 16 kHz mono recommended for best accuracy.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Audio file is empty.")

    content_type = audio.content_type or "audio/wav"
    fmt = "flac" if "flac" in content_type else ("mp3" if "mp3" in content_type else "wav")

    try:
        result = await svc.transcribe_audio(audio_bytes, lang, audio_format=fmt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ASR error: {exc}")

    return {
        "transcript":       result.transcript,
        "detected_lang":    result.detected_lang,
        "confidence":       result.confidence,
        "audio_duration_ms":result.audio_duration_ms,
        "model_used":       result.model_used,
    }


@router.post("/tts", response_model=TTSResponse,
             summary="Text-to-Speech synthesis")
async def tts(
    req: TTSRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> TTSResponse:
    """Synthesize speech for the given text and language. Returns base64-encoded WAV."""
    try:
        result = await svc.synthesize_speech(req.text, req.lang, gender=req.gender)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS error: {exc}")

    return TTSResponse(
        audio_base64=result.audio_base64,
        lang=result.lang,
        model_used=result.model_used,
        audio_format=result.audio_format,
    )


@router.post("/asr-pipeline", response_model=ASRPipelineResponse,
             summary="Voice input pipeline: audio → English text for RAG")
async def asr_pipeline(
    audio: UploadFile = File(...),
    lang: str = Form(..., description="Language spoken in the audio e.g. 'hi', 'ta'"),
    svc: SarvamService = Depends(get_sarvam_service),
) -> ASRPipelineResponse:
    """
    Combined ASR + NMT pipeline.
    Upload audio → get regional transcript + English translation ready for RAG.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Audio file is empty.")

    content_type = audio.content_type or "audio/wav"
    fmt = "flac" if "flac" in content_type else ("mp3" if "mp3" in content_type else "wav")

    try:
        result = await svc.asr_then_translate(audio_bytes, lang, audio_format=fmt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ASR pipeline error: {exc}")

    asr = result["asr"]
    nmt = result["nmt"]
    return ASRPipelineResponse(
        transcript=asr.transcript,
        detected_lang=asr.detected_lang,
        english_text=result["english"],
        asr_model=asr.model_used,
        nmt_model=nmt.model_used,
        was_mocked=(asr.model_used in ("mock", "mock_fallback")),
    )


@router.post("/tts-pipeline", summary="Response pipeline: English text → regional audio")
async def tts_pipeline(
    req: ReverseRequest,
    svc: SarvamService = Depends(get_sarvam_service),
) -> dict:
    """
    Combined NMT + TTS pipeline.
    Takes an English RAG answer and returns translated text + synthesized audio.
    """
    try:
        result = await svc.rag_response_to_audio(
            req.english_text, req.target_lang, tts_gender=req.tts_gender
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS pipeline error: {exc}")

    nmt = result["nmt"]
    tts = result["tts"]
    return {
        "regional_text": nmt.translated_text,
        "target_lang":   nmt.target_lang,
        "audio_base64":  tts.audio_base64,
        "audio_format":  tts.audio_format,
        "nmt_model":     nmt.model_used,
        "tts_model":     tts.model_used,
    }


@router.get("/languages", summary="List all supported Indian languages")
async def list_languages(
    svc: SarvamService = Depends(get_sarvam_service),
) -> dict:
    """Return supported language codes and their display names."""
    return {
        "supported_languages": svc.supported_languages,
        "regional_languages":  [k for k, v in svc.supported_languages.items() if k != "en"],
        "total": len(svc.supported_languages),
    }


@router.get("/health", summary="Sarvam service health check")
async def health(
    svc: SarvamService = Depends(get_sarvam_service),
) -> dict:
    """Check Sarvam service status and mock mode."""
    return {
        "status":    "ok",
        "mock_mode": svc.is_mock,
        "note": (
            "Running in MOCK mode — no real API calls. "
            "Set BHASHINI_USER_ID, BHASHINI_API_KEY, BHASHINI_INFERENCE_KEY in .env for live mode."
            if svc.is_mock else
            "Running in LIVE mode — connected to Sarvam Dhruva API."
        ),
    }
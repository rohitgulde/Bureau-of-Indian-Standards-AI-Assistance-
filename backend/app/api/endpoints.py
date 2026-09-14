"""
app/api/endpoints.py
─────────────────────
Frontend-facing REST + WebSocket API surface for the BIS Knowledge Portal.

This module is the single integration point that the Next.js frontend talks to.
It composes all backend services into four clean endpoints:

  POST   /api/chat            — SSE streaming chat with conversation history,
                                multilingual support, and citation metadata events.
  WS     /ws/chat             — WebSocket variant of the same pipeline for
                                real-time bidirectional chat.
  POST   /api/voice-chat      — Full voice pipeline:
                                audio → Bhashini ASR → QueryRouter → Bhashini TTS
                                Returns audio bytes (base64) + text answer.
  GET    /api/labs            — Lab search with state / city / product filters.
  GET    /api/schemes         — All certification scheme workflows.

CORS
----
Configured in main.py (allow_origins includes http://localhost:3000).
No duplicate middleware here — see main.py for the CORSMiddleware setup.

SSE streaming protocol (POST /api/chat)
----------------------------------------
Each SSE event is a JSON-encoded dict.  Three event types are emitted:

  { "type": "token",    "data": "<text_chunk>" }
      Streamed as Gemini generates — one per token/chunk.

  { "type": "metadata", "data": { intent, lang, citations, fallback, ... } }
      Sent once after all tokens — contains full structured result.

  { "type": "error",    "data": "<error_message>" }
      Sent if the pipeline fails.

  { "type": "done" }
      Final sentinel — client should close the stream.

WebSocket message protocol (/ws/chat)
--------------------------------------
  Client → Server:  JSON  { "question": "...", "lang": "hi", "history": [...] }
  Server → Client:  JSON stream, same type/data format as SSE above.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from typing import Any, AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database.session import SessionLocal
from app.models.db_models import CertificationScheme, Laboratory
from app.services.sarvam_service import SarvamService, get_sarvam_service
from app.services.query_router import Intent, QueryRouter, RouterResponse
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Frontend API"])


# =============================================================================
# Singleton service dependencies
# =============================================================================

_query_router: QueryRouter | None = None
_rag_service:  RAGService  | None = None


def get_router() -> QueryRouter:
    global _query_router
    if _query_router is None:
        try:
            _query_router = QueryRouter.from_env()
        except Exception as exc:
            raise HTTPException(503, f"Query router unavailable: {exc}")
    return _query_router


def get_rag() -> RAGService:
    global _rag_service
    if _rag_service is None:
        try:
            _rag_service = RAGService.from_env()
        except Exception as exc:
            raise HTTPException(503, f"RAG service unavailable: {exc}")
    return _rag_service


# =============================================================================
# Shared helpers
# =============================================================================

def _format_sse(event_type: str, data: Any) -> str:
    """Encode one SSE frame."""
    payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _citations_to_list(rag_resp) -> list[dict]:
    """Serialise Citation dataclasses to JSON-safe dicts."""
    if rag_resp is None:
        return []
    return [asdict(c) for c in rag_resp.citations]


_REFORMULATE_PROMPT = """\
Given a chat history and the latest user question, formulate a standalone question that can be understood without the chat history.
Do NOT answer the question, just reformulate it if needed.
If the question is already clear, return it exactly as is.

Chat History:
{chat_history}

Latest Question: {question}

Standalone Question:"""

async def _reformulate_query(question: str, history: list[ConversationMessage], qr: QueryRouter) -> str:
    """Uses the classifier LLM to contextualize the current query based on history."""
    if not history:
        return question
        
    recent = history[-6:]
    history_text = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
        for m in recent
    )
    
    prompt = _REFORMULATE_PROMPT.format(chat_history=history_text, question=question)
    try:
        response = await qr._classifier_llm.ainvoke(prompt)
        text = response.content
        if isinstance(text, list):
            text = text[0].get("text", "") if isinstance(text[0], dict) else str(text[0])
        text = text.strip()
        logger.info(f"Query reformulated: '{question}' -> '{text}'")
        return text
    except Exception as exc:
        logger.warning(f"Query reformulation failed: {exc}. Using original question with context fallback.")
        last_assistant = next((m.content for m in reversed(history) if m.role == 'assistant'), "")
        if last_assistant:
            return f"{last_assistant}\n[Current question]{question}"
        return question


def _build_metadata(
    result: RouterResponse,
    original_lang: str,
    translated_question: str | None,
    regional_answer: str | None,
) -> dict[str, Any]:
    """Build the metadata SSE payload from a RouterResponse."""
    rag = result.rag_response
    return {
        "intent":              result.intent.value,
        "detected_lang":       original_lang,
        "translated_question": translated_question,
        "answer":              rag.answer if rag else None,
        "regional_answer":     regional_answer,
        "citations":           _citations_to_list(rag),
        "num_chunks":          rag.num_chunks_retrieved if rag else 0,
        "fallback_triggered":  rag.fallback_triggered   if rag else False,
        "model_used":          rag.model_used            if rag else None,
        "labs":                result.labs,
        "schemes":             result.schemes,
        "faqs":                result.faqs,
        "huid_verification":   result.huid_verification,
        "process_explainer":   result.process_explainer,
        "error":               result.error,
        "pipeline_ms":         result.pipeline_latency_ms,
        "classification": {
            "stage":      result.classification.stage,
            "confidence": result.classification.confidence,
        },
    }


# =============================================================================
# Pydantic schemas
# =============================================================================

class ConversationMessage(BaseModel):
    role: str    = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text in the conversation language.")


class ChatRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=2000,
        description="User query in any supported language.",
        examples=["IS 10500 में पानी का pH सीमा क्या है?"],
    )
    language_code: str | None = Field(
        "en-IN",
        description="Sarvam ISO-639-1 language code hint (e.g. 'en-IN', 'hi-IN').",
    )
    history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Prior conversation turns for context (last 20 kept).",
    )
    stream: bool = Field(
        True,
        description="If False, return complete JSON instead of SSE stream.",
    )


class LabsResponse(BaseModel):
    total: int
    labs: list[dict[str, Any]]
    filters_applied: dict[str, Any]


class SchemesResponse(BaseModel):
    total: int
    schemes: list[dict[str, Any]]

# =============================================================================
# POST /api/chat  — SSE streaming with conversation history + citations
# =============================================================================

async def _run_chat_pipeline(
    question: str,
    history: list[ConversationMessage],
    language_code: str,
    qr: QueryRouter,
    sarvam: SarvamService,
) -> tuple[str, str | None, RouterResponse]:
    """
    Core pipeline shared by both SSE and WebSocket endpoints.

    Returns
    -------
    (english_question, translated_question_or_None, RouterResponse)
    """
    # 1. Translate question to English if needed
    if language_code != "en-IN":
        english_q = await sarvam.translate_text(question, source_lang=language_code, target_lang="en-IN")
        translated_q = english_q
        detected_lang = language_code[:2] if language_code else "en"
    else:
        english_q = question
        translated_q = None
        detected_lang = "en"

    # 2. Build context-enriched question from conversation history
    full_english_q = await _reformulate_query(english_q, history, qr)

    # 3. Route through QueryRouter
    result: RouterResponse = await qr.route(full_english_q)
    return detected_lang, translated_q, result


async def _stream_chat_sse(
    question: str,
    history: list[ConversationMessage],
    language_code: str,
    qr: QueryRouter,
    rag: RAGService,
    sarvam: SarvamService,
) -> AsyncIterator[str]:
    """
    Async generator that yields SSE-formatted strings.

    Token events stream as Gemini generates.  After streaming is complete,
    one metadata event carries citation objects, intent, labs, schemes, faqs.
    If the response needs reverse-translation, it is included in metadata.
    """
    detected_lang = "en"
    translated_q:  str | None = None
    regional_answer: str | None = None

    try:
        # ── Step 1: Translate to English if needed ────────────────────────
        if language_code and language_code != "en-IN":
            english_q = await sarvam.translate_text(question, source_lang=language_code, target_lang="en-IN")
            translated_q = english_q
            detected_lang = language_code[:2]
        else:
            english_q = question
            translated_q = None
            detected_lang = "en"

        # ── Step 2: Enrich with conversation history ──────────────────────
        full_english_q = await _reformulate_query(english_q, history, qr)

        # ── Step 3: Classify intent ───────────────────────────────────────
        classification = await qr.classify(full_english_q)
        intent = classification.intent

        # ── Step 4: Stream tokens (RAG intents) or run pipeline directly ──
        accumulated_tokens: list[str] = []

        if intent in (Intent.TECHNICAL_CLAUSE_QUERY, Intent.PRODUCT_STANDARD_LOOKUP):
            # Emit tokens live via RAGService.stream()
            async for token in rag.stream(question=full_english_q, top_k=8):
                accumulated_tokens.append(token)
                # Only stream English tokens live if the user is in English mode
                if language_code == "en-IN":
                    yield _format_sse("token", token)

        else:
            # Non-RAG intents (LAB_SEARCH, SCHEME_GUIDANCE, CONSUMER_HALLMARK)
            if language_code == "en-IN":
                yield _format_sse("token", "")   # empty prime so client knows stream started

        # ── Step 5: Run full pipeline (always) to get structured metadata ─
        result: RouterResponse = await qr.route(
            full_english_q, classification=classification
        )

        # Patch the accumulated answer into rag_response if it was streamed
        if accumulated_tokens and result.rag_response:
            result.rag_response.answer = "".join(accumulated_tokens)

        # ── Step 6: Reverse translation if needed ─────────────────────────
        answer_en = ""
        regional_answer = None
        if getattr(result, "rag_response", None):
            answer_en = result.rag_response.answer
        elif intent == Intent.CONSUMER_HALLMARK and result.faqs:
            answer_en = "Here is a relevant FAQ that answers your question:"
        elif intent == Intent.SCHEME_GUIDANCE and result.schemes:
            answer_en = "Here are the relevant certification schemes for your query:"
        elif intent == Intent.PROCESS_EXPLAINER and result.process_explainer:
            answer_en = result.process_explainer["markdown"]

        if answer_en and language_code and language_code != "en-IN":
            logger.info(f"Translating answer_en to {language_code}: {answer_en[:50]}...")
            regional_answer = await sarvam.translate_text(answer_en, source_lang="en-IN", target_lang=language_code)
            logger.info(f"Resulting regional_answer: {regional_answer[:50]}...")
            # Stream translated answer tokens (chunked by sentence)
            for chunk in _chunk_text(regional_answer, size=80):
                yield _format_sse("token", chunk)
        else:
            if answer_en:
                if not accumulated_tokens or language_code != "en-IN":
                    yield _format_sse("token", answer_en)
            else:
                yield _format_sse("token", "")

        # ── Step 7: Metadata event ────────────────────────────────────────
        meta = _build_metadata(result, detected_lang, translated_q, regional_answer)
        yield _format_sse("metadata", meta)

    except Exception as exc:
        logger.exception("SSE pipeline error: %s", exc)
        yield _format_sse("error", str(exc))

    finally:
        yield _format_sse("done", None)


def _chunk_text(text: str, size: int = 80) -> list[str]:
    """Split text into roughly sentence-sized SSE chunks."""
    import re
    sentences = re.split(r"(?<=[।.!?])\s+", text)
    chunks, buf = [], ""
    for s in sentences:
        buf += s + " "
        if len(buf) >= size:
            chunks.append(buf.rstrip())
            buf = ""
    if buf.strip():
        chunks.append(buf.rstrip())
    return chunks or [text]


@router.post(
    "/api/chat",
    summary="Streaming chat — SSE token stream with citation metadata",
    description=(
        "Accepts a query in any Indian language + conversation history. "
        "Streams LLM tokens as Server-Sent Events. "
        "Emits a final `metadata` event with citations, intent, labs, schemes, FAQs. "
        "Set `stream: false` for a single-shot JSON response."
    ),
    response_class=StreamingResponse,
)
async def chat(
    req: ChatRequest,
    qr:       QueryRouter   = Depends(get_router),
    rag:      RAGService    = Depends(get_rag),
    sarvam: SarvamService = Depends(get_sarvam_service),
):
    """
    Main chat endpoint consumed by the Next.js frontend.

    SSE stream format::

        data: {"type":"token",    "data":"[Standard: IS 10500"}\\n\\n
        data: {"type":"token",    "data":", Clause: 4.1]..."}\\n\\n
        data: {"type":"metadata", "data":{...citations, intent, labs...}}\\n\\n
        data: {"type":"done",     "data":null}\\n\\n

    Non-streaming (stream=false) returns a single JSON object.
    """
    if not req.stream:
        # Non-streaming path: run pipeline, return JSON
        detected_lang, translated_q, result = await _run_chat_pipeline(
            req.question, req.history, req.language_code, qr, sarvam
        )
        rag_resp = result.rag_response
        regional_answer: str | None = None

        answer_en = ""
        if getattr(result, "rag_response", None):
            answer_en = result.rag_response.answer
        elif result.intent == Intent.CONSUMER_HALLMARK and result.faqs:
            answer_en = "Here is a relevant FAQ that answers your question:"
        elif result.intent == Intent.SCHEME_GUIDANCE and result.schemes:
            answer_en = "Here are the relevant certification schemes for your query:"
        elif result.intent == Intent.PROCESS_EXPLAINER and result.process_explainer:
            answer_en = result.process_explainer["markdown"]

        if answer_en and req.language_code and req.language_code != "en-IN":
            regional_answer = await sarvam.translate_text(answer_en, source_lang="en-IN", target_lang=req.language_code)

        from fastapi.responses import JSONResponse
        return JSONResponse(content={
            "answer":          answer_en,
            "regional_answer": regional_answer,
            **_build_metadata(result, detected_lang, translated_q, regional_answer),
        })

    return StreamingResponse(
        _stream_chat_sse(req.question, req.history, req.language_code, qr, rag, sarvam),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# =============================================================================
# WS /ws/chat  — WebSocket streaming chat
# =============================================================================

@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket,
    qr:       QueryRouter    = Depends(get_router),
    rag:      RAGService     = Depends(get_rag),
    sarvam: SarvamService = Depends(get_sarvam_service),
):
    """
    WebSocket chat endpoint — mirrors SSE protocol over a persistent connection.

    Client sends JSON::

        { "question": "IS 10500 pH limit?", "lang": "hi", "history": [...] }

    Server streams JSON messages::

        { "type": "token",    "data": "<chunk>" }
        { "type": "metadata", "data": { citations, intent, labs, ... } }
        { "type": "done",     "data": null }

    Connection stays open between turns — client sends the next question
    after receiving `done`.  On error the connection is closed with code 1011.
    """
    await websocket.accept()
    logger.info("WebSocket /ws/chat connected from %s", websocket.client)

    try:
        while True:
            # Receive next user message
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "data": "Invalid JSON payload."})
                )
                continue

            question = msg.get("question", "").strip()
            history_raw = msg.get("history", [])
            language_code = msg.get("lang", "en-IN")
            # If client passes 2-letter code, upgrade it to -IN
            if len(language_code) == 2:
                language_code = f"{language_code}-IN"
            
            history = [
                ConversationMessage(role=m.get("role", "user"), content=m.get("content", ""))
                for m in history_raw
                if isinstance(m, dict)
            ]

            if not question:
                await websocket.send_text(
                    json.dumps({"type": "error", "data": "Empty question."})
                )
                continue

            # Stream pipeline output over WebSocket
            async for sse_frame in _stream_chat_sse(question, history, language_code, qr, rag, sarvam):
                # sse_frame is "data: {json}\n\n" — extract just the JSON
                json_part = sse_frame.removeprefix("data: ").strip()
                await websocket.send_text(json_part)

    except WebSocketDisconnect:
        logger.info("WebSocket /ws/chat disconnected")
    except Exception as exc:
        logger.exception("WebSocket error: %s", exc)
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "data": str(exc)})
            )
            await websocket.close(code=1011)
        except Exception:
            pass


# =============================================================================
# POST /api/voice-chat  — Full voice pipeline (ASR → Router → TTS)
# =============================================================================

@router.post(
    "/api/voice-chat",
    summary="Voice chat — audio in, audio + text out",
    description=(
        "Full multimodal pipeline: upload audio → Bhashini ASR → "
        "QueryRouter (intent classify + answer) → Bhashini TTS. "
        "Returns the English answer text, regional translated text, "
        "and base64-encoded WAV audio of the regional answer."
    ),
)
async def voice_chat(
    audio:    UploadFile = File(...,  description="Audio file (WAV/FLAC/MP3, 16 kHz mono)."),
    lang:     str        = Form(...,  description="Language spoken in audio e.g. 'hi', 'ta'."),
    tts_gender: str      = Form("female", description="TTS voice: 'male' | 'female'."),
    qr:       QueryRouter    = Depends(get_router),
    sarvam: SarvamService = Depends(get_sarvam_service),
) -> dict[str, Any]:
    """
    Voice-to-voice pipeline.

    Response fields
    ---------------
    transcript        — what the user said (regional language)
    english_question  — translated to English for RAG
    english_answer    — AI answer in English
    regional_answer   — AI answer translated back to user's language
    audio_base64      — synthesized WAV of regional_answer (base64)
    intent            — classified intent
    citations         — list of IS clause citations
    was_mocked        — True when Bhashini API is in mock mode
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(422, "Audio file is empty.")

    content_type = audio.content_type or "audio/wav"
    fmt = "flac" if "flac" in content_type else ("mp3" if "mp3" in content_type else "wav")

    # ── Step 1: ASR — audio → regional transcript ─────────────────────────
    try:
        asr = await sarvam.transcribe_audio(audio_bytes, lang, audio_format=fmt)
    except Exception as exc:
        raise HTTPException(502, f"ASR failed: {exc}")

    transcript = asr.transcript
    if not transcript.strip():
        raise HTTPException(422, "ASR returned empty transcript. Check audio quality.")

    # ── Step 2: NMT forward — regional transcript → English ───────────────
    try:
        nmt_fwd = await sarvam.translate_to_english(transcript, lang)
        english_q = nmt_fwd.translated_text
    except Exception as exc:
        logger.warning("NMT forward failed, using transcript directly: %s", exc)
        english_q = transcript

    # ── Step 3: QueryRouter — classify + answer ───────────────────────────
    try:
        result: RouterResponse = await qr.route(english_q)
    except Exception as exc:
        raise HTTPException(502, f"Query router failed: {exc}")

    rag_resp = result.rag_response
    english_answer = rag_resp.answer if rag_resp else (
        "I found the information you need. Please check the structured results."
    )

    # ── Step 4: NMT reverse — English answer → regional ──────────────────
    regional_answer = english_answer
    try:
        if lang not in ("en", "unknown"):
            nmt_rev = await sarvam.translate_from_english(english_answer, lang)
            regional_answer = nmt_rev.translated_text
    except Exception as exc:
        logger.warning("NMT reverse failed, using English: %s", exc)

    # ── Step 5: TTS — regional text → speech ─────────────────────────────
    audio_b64: str | None = None
    tts_model = "skipped"
    try:
        tts = await sarvam.synthesize_speech(regional_answer, lang, gender=tts_gender)
        audio_b64 = tts.audio_base64
        tts_model = tts.model_used
    except Exception as exc:
        logger.warning("TTS failed (non-fatal): %s", exc)

    return {
        "transcript":       transcript,
        "english_question": english_q,
        "english_answer":   english_answer,
        "regional_answer":  regional_answer,
        "audio_base64":     audio_b64,
        "audio_format":     "wav",
        "lang":             lang,
        "intent":           result.intent.value,
        "citations":        _citations_to_list(rag_resp),
        "labs":             result.labs,
        "schemes":          result.schemes,
        "faqs":             result.faqs,
        "models": {
            "asr": asr.model_used,
            "nmt": nmt_fwd.model_used if "nmt_fwd" in dir() else "passthrough",
            "tts": tts_model,
        },
        "was_mocked": sarvam.is_mock,
    }


# =============================================================================
# GET /api/labs  — Lab search with filters
# =============================================================================

@router.get(
    "/api/labs",
    response_model=LabsResponse,
    summary="Search BIS-recognised testing laboratories",
    description=(
        "Query the labs database with optional filters. "
        "Supports state, city, and product/testing-scope keyword filters."
    ),
)
def get_labs(
    state:   str | None = Query(None, description="Filter by state e.g. 'Delhi', 'Maharashtra'."),
    city:    str | None = Query(None, description="Filter by city e.g. 'Mumbai', 'Bengaluru'."),
    product: str | None = Query(None, description="Testing scope keyword e.g. 'cement', 'LED'."),
    limit:   int        = Query(20, ge=1, le=100, description="Max results (default 20)."),
    offset:  int        = Query(0,  ge=0,          description="Pagination offset."),
) -> LabsResponse:
    """
    Returns active labs matching the filter criteria.

    Filters are combined with AND logic.
    If no filters are provided, returns all active labs (up to limit).
    """
    db = SessionLocal()
    try:
        q = db.query(Laboratory).filter(Laboratory.is_active == True)

        if state:
            q = q.filter(Laboratory.state.ilike(f"%{state}%"))
        if city:
            q = q.filter(Laboratory.city.ilike(f"%{city}%"))
        if product:
            q = q.filter(Laboratory.testing_scope.ilike(f"%{product}%"))

        total = q.count()
        labs  = q.order_by(Laboratory.state, Laboratory.city, Laboratory.name) \
                  .offset(offset).limit(limit).all()

        return LabsResponse(
            total=total,
            labs=[
                {
                    "id":            l.id,
                    "name":          l.name,
                    "city":          l.city,
                    "state":         l.state,
                    "pincode":       l.pincode,
                    "address":       l.address,
                    "phone":         l.phone,
                    "contact_email": l.contact_email,
                    "website":       l.website,
                    "accreditations":l.accreditations,
                    "testing_scope": l.testing_scope,
                    "latitude":      l.latitude,
                    "longitude":     l.longitude,
                }
                for l in labs
            ],
            filters_applied={"state": state, "city": city, "product": product},
        )
    finally:
        db.close()


# =============================================================================
# GET /api/schemes  — All certification scheme workflows
# =============================================================================

@router.get(
    "/api/schemes",
    response_model=SchemesResponse,
    summary="Fetch all BIS certification scheme workflows",
    description="Returns all active certification schemes with full workflow description.",
)
def get_schemes(
    mandatory: bool | None = Query(None, description="Filter: true=mandatory only, false=voluntary only."),
    audience:  str  | None = Query(None, description="Filter by target audience e.g. 'Importer'."),
    limit:     int         = Query(50, ge=1, le=200),
    offset:    int         = Query(0,  ge=0),
) -> SchemesResponse:
    """
    Returns all active BIS certification schemes.

    Each scheme includes:
    - Full workflow description (step-by-step)
    - Portal URL, turnaround time, fee note
    - Target audience and applicable products
    - Mandatory / voluntary classification
    """
    db = SessionLocal()
    try:
        q = db.query(CertificationScheme).filter(CertificationScheme.is_active == True)

        if mandatory is not None:
            val = "Mandatory" if mandatory else "Voluntary"
            q = q.filter(CertificationScheme.mandatory_or_voluntary.ilike(f"%{val}%"))
        if audience:
            q = q.filter(CertificationScheme.target_audience.ilike(f"%{audience}%"))

        total   = q.count()
        schemes = q.order_by(CertificationScheme.scheme_code) \
                   .offset(offset).limit(limit).all()

        return SchemesResponse(
            total=total,
            schemes=[
                {
                    "id":                     s.id,
                    "scheme_name":            s.scheme_name,
                    "scheme_code":            s.scheme_code,
                    "target_audience":        s.target_audience,
                    "mandatory_or_voluntary": s.mandatory_or_voluntary,
                    "governing_regulation":   s.governing_regulation,
                    "applicable_products":    s.applicable_products,
                    "application_portal_url": s.application_portal_url,
                    "standard_turnaround_time": s.standard_turnaround_time,
                    "fee_structure_note":     s.fee_structure_note,
                    "validity_period":        s.validity_period,
                    "description":            s.description,
                }
                for s in schemes
            ],
        )
    finally:
        db.close()

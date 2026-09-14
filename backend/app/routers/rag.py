"""
app/routers/rag.py
───────────────────
FastAPI router that exposes the RAG service over HTTP.

Endpoints
---------
POST  /api/rag/query      — Full round-trip: returns structured RAGResponse JSON
GET   /api/rag/stream     — Server-Sent Events streaming response
GET   /api/rag/health     — Checks Qdrant collection stats
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.rag_service import RAGResponse, RAGService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG — IS Standards QA"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency: singleton RAGService (initialised once at startup)
# ─────────────────────────────────────────────────────────────────────────────

_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """FastAPI dependency that returns the singleton RAGService."""
    global _rag_service
    if _rag_service is None:
        try:
            _rag_service = RAGService.from_env()
        except Exception as exc:
            logger.error("Failed to initialise RAGService: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"RAG service unavailable: {exc}",
            )
    return _rag_service


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    """Request body for POST /api/rag/query."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language query about an Indian Standard.",
        examples=["What is the permissible limit for turbidity in IS 10500?"],
    )
    standard_code: str | None = Field(
        None,
        description="Optional filter: restrict retrieval to this IS standard e.g. 'IS 10500:2012'.",
    )
    product_category: str | None = Field(
        None,
        description="Optional filter by product category e.g. 'Drinking Water'.",
    )
    top_k: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Number of IS standard chunks to retrieve from Qdrant.",
    )
    use_pro_model: bool = Field(
        default=False,
        description="If True, uses gemini-1.5-pro (slower, higher quality). "
                    "Default: gemini-1.5-flash.",
    )


class CitationOut(BaseModel):
    standard_code: str
    clause_number: str
    clause_title: str
    page_number: int
    score: float
    excerpt: str


class RAGQueryResponse(BaseModel):
    """Response body for POST /api/rag/query."""

    answer: str = Field(description="Grounded, cited answer from Gemini.")
    citations: list[CitationOut] = Field(
        description="Structured list of IS clauses cited in the answer."
    )
    num_chunks_retrieved: int
    fallback_triggered: bool = Field(
        description="True if the zero-hallucination fallback phrase was triggered."
    )
    model_used: str
    query: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Query IS standards using RAG",
    description=(
        "Embeds the question, retrieves relevant IS-standard clauses from Qdrant, "
        "and generates a strictly grounded, cited answer using Gemini 1.5."
    ),
)
async def rag_query(
    request: RAGQueryRequest,
    svc: RAGService = Depends(get_rag_service),
) -> RAGQueryResponse:
    """
    Full RAG pipeline in one shot.

    - Retrieves top-K IS clauses from Qdrant by semantic similarity.
    - Injects them as grounded context into a strict system prompt.
    - Generates a cited answer via Gemini — every fact prefixed with
      [Standard: IS XXXX, Clause: Y.Z].
    - Returns structured citations alongside the answer.
    """
    # Optionally switch to Pro for this request
    if request.use_pro_model:
        import os
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        from app.services.rag_service import RAGService as _RS, DEFAULT_MODEL_PRO
        query_svc = _RS(
            vector_service=svc._vector_svc,
            model_name=DEFAULT_MODEL_PRO,
            top_k=request.top_k,
            google_api_key=api_key,
        )
    else:
        query_svc = svc

    try:
        result: RAGResponse = await query_svc.query(
            question=request.question,
            standard_code=request.standard_code,
            product_category=request.product_category,
            top_k=request.top_k,
        )
    except Exception as exc:
        logger.exception("RAG query failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {exc}")

    return RAGQueryResponse(
        answer=result.answer,
        citations=[CitationOut(**asdict(c)) for c in result.citations],
        num_chunks_retrieved=result.num_chunks_retrieved,
        fallback_triggered=result.fallback_triggered,
        model_used=result.model_used,
        query=result.query,
    )


@router.get(
    "/stream",
    summary="Stream an IS standard RAG answer (SSE)",
    description=(
        "Streams the Gemini response token-by-token as Server-Sent Events (SSE). "
        "Retrieval happens synchronously before streaming begins — grounding rules apply."
    ),
    response_class=StreamingResponse,
)
async def rag_stream(
    question: str = Query(
        ...,
        min_length=3,
        max_length=1000,
        description="Your IS-standard question.",
    ),
    standard_code: str | None = Query(None),
    product_category: str | None = Query(None),
    top_k: int = Query(default=8, ge=1, le=20),
    svc: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """
    Server-Sent Events streaming endpoint.

    Each event is a raw text token in the format::

        data: <token>\\n\\n

    The client can reconstruct the full answer by joining all tokens.
    The grounding contract (citations, fallback) still applies — the
    structured citation block streams at the end of the response.
    """
    async def _generate() -> AsyncIterator[str]:
        try:
            async for token in svc.stream(
                question=question,
                standard_code=standard_code,
                product_category=product_category,
                top_k=top_k,
            ):
                # SSE format: each token as a data event
                yield f"data: {token}\n\n"
        except Exception as exc:
            logger.error("Streaming RAG error: %s", exc)
            yield f"data: [ERROR] {exc}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",   # disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/health",
    summary="RAG + Qdrant health check",
    description="Returns Qdrant collection stats and RAG service configuration.",
)
async def rag_health(
    svc: RAGService = Depends(get_rag_service),
) -> dict:
    """Check that the RAG service and Qdrant are healthy."""
    try:
        info = svc._vector_svc.get_collection_info()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Qdrant unreachable: {exc}")

    return {
        "status": "ok",
        "model": svc._model_name,
        "top_k": svc._top_k,
        "qdrant_collection": info,
    }
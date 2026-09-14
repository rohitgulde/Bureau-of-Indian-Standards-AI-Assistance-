"""
app/routers/chat.py
────────────────────
FastAPI router exposing the QueryRouter as a single /api/chat endpoint.

All five intent pipelines flow through this one route —
the client never needs to know which backend pipeline handled a request.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.query_router import Intent, QueryRouter, RouterResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat — Query Router"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency: singleton QueryRouter
# ─────────────────────────────────────────────────────────────────────────────

_router_singleton: QueryRouter | None = None


def get_query_router() -> QueryRouter:
    global _router_singleton
    if _router_singleton is None:
        try:
            _router_singleton = QueryRouter.from_env()
        except Exception as exc:
            logger.error("Failed to initialise QueryRouter: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Query router unavailable: {exc}",
            )
    return _router_singleton


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User's natural language question about BIS / IS standards.",
        examples=[
            "What is the permissible pH limit in IS 10500?",
            "Where can I test my PVC pipes in Delhi?",
            "How do I apply for an ISI Mark licence?",
            "How do I verify HUID on my gold jewellery?",
        ],
    )


class ClassificationOut(BaseModel):
    intent: str
    confidence: float
    stage: str
    latency_ms: float


class LabOut(BaseModel):
    id: int
    name: str
    city: str
    state: str
    pincode: str
    address: str
    phone: str | None
    contact_email: str | None
    website: str | None
    accreditations: str
    testing_scope: str
    latitude: str | None
    longitude: str | None


class SchemeOut(BaseModel):
    id: int
    scheme_name: str
    scheme_code: str
    target_audience: str
    mandatory_or_voluntary: str
    application_portal_url: str | None
    standard_turnaround_time: str | None
    description: str | None


class FAQOut(BaseModel):
    id: int
    topic: str
    category: str
    question: str
    resolution_steps: str
    related_url: str | None
    related_scheme: str | None


class CitationOut(BaseModel):
    standard_code: str
    clause_number: str
    clause_title: str
    page_number: int
    score: float
    excerpt: str


class ChatResponse(BaseModel):
    """
    Unified response for all five intents.
    Only the fields relevant to the detected intent are populated.
    """
    intent: str
    query: str
    classification: ClassificationOut
    pipeline_latency_ms: float

    # RAG-based intents
    answer: str | None = None
    citations: list[CitationOut] = []
    num_chunks_retrieved: int = 0
    fallback_triggered: bool = False

    # DB-based intents
    labs: list[LabOut] = []
    schemes: list[SchemeOut] = []
    faqs: list[FAQOut] = []
    huid_verification: dict | None = None

    error: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ChatResponse,
    summary="BIS Knowledge Portal — unified chat endpoint",
    description=(
        "Routes the question through a two-stage intent classifier "
        "(keyword heuristics → Gemini Flash fallback) and dispatches to "
        "the appropriate specialised pipeline: RAG, Lab Search, Scheme Guidance, "
        "Consumer Hallmark FAQ, or Product Standard Lookup."
    ),
)
async def chat(
    request: ChatRequest,
    qr: QueryRouter = Depends(get_query_router),
) -> ChatResponse:
    """
    Single entry-point for all BIS queries.

    The response ``intent`` field tells the frontend which UI layout to render:
    - ``TECHNICAL_CLAUSE_QUERY`` / ``PRODUCT_STANDARD_LOOKUP`` → Citation panel
    - ``LAB_SEARCH``             → Map / lab card list
    - ``SCHEME_GUIDANCE``        → Scheme cards + citation panel
    - ``CONSUMER_HALLMARK``      → FAQ cards + optional citation panel
    """
    try:
        result: RouterResponse = await qr.route(request.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # ── Flatten RAGResponse fields ────────────────────────────────────────
    answer               = None
    citations_out: list[CitationOut] = []
    num_chunks           = 0
    fallback             = False

    if result.rag_response:
        rr = result.rag_response
        answer      = rr.answer
        num_chunks  = rr.num_chunks_retrieved
        fallback    = rr.fallback_triggered
        citations_out = [
            CitationOut(
                standard_code=c.standard_code,
                clause_number=c.clause_number,
                clause_title=c.clause_title,
                page_number=c.page_number,
                score=c.score,
                excerpt=c.excerpt,
            )
            for c in rr.citations
        ]

    cls = result.classification
    return ChatResponse(
        intent=result.intent.value,
        query=result.query,
        classification=ClassificationOut(
            intent=cls.intent.value,
            confidence=cls.confidence,
            stage=cls.stage,
            latency_ms=cls.latency_ms,
        ),
        pipeline_latency_ms=result.pipeline_latency_ms,
        answer=answer,
        citations=citations_out,
        num_chunks_retrieved=num_chunks,
        fallback_triggered=fallback,
        labs=[LabOut(**lab) for lab in result.labs],
        schemes=[
            SchemeOut(
                id=s["id"],
                scheme_name=s["scheme_name"],
                scheme_code=s["scheme_code"],
                target_audience=s["target_audience"],
                mandatory_or_voluntary=s["mandatory_or_voluntary"],
                application_portal_url=s.get("application_portal_url"),
                standard_turnaround_time=s.get("standard_turnaround_time"),
                description=s.get("description"),
            )
            for s in result.schemes
        ],
        faqs=[FAQOut(**faq) for faq in result.faqs],
        error=result.error,
        huid_verification=result.huid_verification
    )


@router.post(
    "/classify",
    summary="Classify query intent (without running the pipeline)",
    description="Useful for debugging or frontend routing decisions.",
)
async def classify_only(
    request: ChatRequest,
    qr: QueryRouter = Depends(get_query_router),
) -> ClassificationOut:
    """Classify a query without running the full pipeline."""
    cls = await qr.classify(request.question)
    return ClassificationOut(
        intent=cls.intent.value,
        confidence=cls.confidence,
        stage=cls.stage,
        latency_ms=cls.latency_ms,
    )
"""
app/services/query_router.py
─────────────────────────────
Lightweight routing agent that classifies every incoming user query into
one of five intents and dispatches it to a dedicated specialized pipeline.

Intent taxonomy
---------------
PRODUCT_STANDARD_LOOKUP   User wants to know which IS standard applies to a product.
TECHNICAL_CLAUSE_QUERY    User asks specific technical requirements (limits, test methods).
LAB_SEARCH                User wants to find an accredited lab to test a product.
SCHEME_GUIDANCE           User wants certification / licensing guidance.
CONSUMER_HALLMARK         User asks about HUID, gold hallmarking, or BIS complaints.

Classification strategy (two-stage, latency-optimised)
-------------------------------------------------------
Stage 1 — Keyword heuristics (< 1 ms, no API call)
    Deterministic regex patterns checked in priority order.
    Covers ~85 % of real-world queries with zero latency.

Stage 2 — LLM classification (Gemini Flash, ~400 ms)
    Invoked only when Stage 1 returns AMBIGUOUS.
    Uses a concise structured prompt that forces a single-word JSON output.

Dispatch
--------
Each intent maps to a specialised async pipeline:

    PRODUCT_STANDARD_LOOKUP  →  _handle_product_lookup()
                                Qdrant semantic search filtered to applicable IS codes.
                                Returns matching standards with clause summaries.

    TECHNICAL_CLAUSE_QUERY   →  _handle_technical_clause()
                                Full RAG pipeline with citation-enforced Gemini answer.

    LAB_SEARCH               →  _handle_lab_search()
                                SQLite query on `laboratories` table.
                                Optionally filtered by city / product keyword.

    SCHEME_GUIDANCE          →  _handle_scheme_guidance()
                                SQLite lookup on `certification_schemes` table +
                                RAG supplement for IS-standard cross-references.

    CONSUMER_HALLMARK        →  _handle_consumer_hallmark()
                                `consumer_faqs` DB lookup + optional RAG supplement.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.db_models import CertificationScheme, ConsumerFAQ, Laboratory
from app.services.rag_service import RAGResponse, RAGService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


# =============================================================================
# Intent enum
# =============================================================================

class Intent(str, Enum):
    PRODUCT_STANDARD_LOOKUP = "PRODUCT_STANDARD_LOOKUP"
    TECHNICAL_CLAUSE_QUERY  = "TECHNICAL_CLAUSE_QUERY"
    LAB_SEARCH              = "LAB_SEARCH"
    SCHEME_GUIDANCE         = "SCHEME_GUIDANCE"
    PROCESS_EXPLAINER       = "PROCESS_EXPLAINER"
    CONSUMER_HALLMARK       = "CONSUMER_HALLMARK"
    GENERAL_QUERY           = "GENERAL_QUERY"
    AMBIGUOUS               = "AMBIGUOUS"   # internal sentinel; never returned to caller


# =============================================================================
# Output dataclasses
# =============================================================================

@dataclass
class ClassificationResult:
    """Outcome of the two-stage intent classifier."""
    intent: Intent
    confidence: float           # 0.0 – 1.0  (1.0 for exact keyword match)
    stage: str                  # "keyword" | "llm"
    raw_query: str
    latency_ms: float


@dataclass
class RouterResponse:
    """
    Unified response returned by QueryRouter.route() for all intents.

    Fields populated differ by intent:
    - TECHNICAL_CLAUSE_QUERY  → rag_response is set
    - LAB_SEARCH              → labs is set
    - SCHEME_GUIDANCE         → schemes is set; rag_response may be set
    - CONSUMER_HALLMARK       → faqs is set; rag_response may be set
    - PRODUCT_STANDARD_LOOKUP → rag_response is set (product-focused RAG)
    """
    intent: Intent
    query: str
    classification: ClassificationResult
    pipeline_latency_ms: float

    # Intent-specific payload fields (at most one or two will be non-empty)
    rag_response: RAGResponse | None = None
    labs: list[dict[str, Any]] = field(default_factory=list)
    schemes: list[dict[str, Any]] = field(default_factory=list)
    faqs: list[dict[str, Any]] = field(default_factory=list)
    huid_verification: dict[str, Any] | None = None
    process_explainer: dict[str, Any] | None = None
    error: str | None = None


# =============================================================================
# Stage-1: Keyword heuristic classifier
# =============================================================================

# Each entry: (pattern, intent, confidence)
# Patterns are checked in order — first match wins.
_KEYWORD_RULES: list[tuple[re.Pattern, Intent, float]] = [

    # ── CONSUMER_HALLMARK (check before general ISI to avoid false positives) ─
    (re.compile(
        r"\b(huid|hallmark|hallmarking|gold\s+jewel|jeweller|karat|carat|ahsc|"
        r"huidonline|22k|18k|14k|916|750|585|"
        r"verify\s+huid|verify\s+gold|check\s+hallmark|check\s+huid|"
        r"spurious\s+hallmark|fake\s+hallmark|wrong\s+purity|refund.*gold)\b",
        re.I,
    ), Intent.CONSUMER_HALLMARK, 0.95),
    
    # 6-character alphanumeric code for HUID verification (must contain at least one digit to avoid english words)
    (re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{6}\b", re.I), Intent.CONSUMER_HALLMARK, 0.99),

    # BIS Care App complaints → CONSUMER_HALLMARK
    (re.compile(
        r"\b(bis\s+care\s+app|lodge\s+complaint|file\s+complaint|"
        r"report.*fake|report.*spurious|bis\s+helpline|1800-11-4000)\b",
        re.I,
    ), Intent.CONSUMER_HALLMARK, 0.90),

    # ── LAB_SEARCH ──────────────────────────────────────────────────────────
    (re.compile(
        r"\b(labs?|laborator(?:y|ies)|testing\s+labs?|accredited\s+labs?|"
        r"nabl\s+labs?|bis\s+recogni[sz]ed\s+labs?|where\s+(can\s+i\s+)?test|"
        r"test\s+my\s+product|get\s+product\s+tested|find\s+(a\s+)?labs?|"
        r"nearby\s+labs?|labs?\s+in\s+(delhi|mumbai|bangalore|bengaluru|chennai|kolkata|pune|hyderabad))\b",
        re.I,
    ), Intent.LAB_SEARCH, 0.95),

    # ── PROCESS_EXPLAINER ───────────────────────────────────────────────────
    (re.compile(
        r"\b(how\s+to\s+(apply|get|obtain|register)|"
        r"(certification|registration|application)\s+(process|steps|procedure|requirement)|"
        r"procedure\s+to\s+(get|apply)|steps\s+for\s+(isi|crs|fmcs|bis)|"
        r"what\s+is\s+the\s+(process|procedure)\b)",
        re.I,
    ), Intent.PROCESS_EXPLAINER, 0.95),

    # ── SCHEME_GUIDANCE ─────────────────────────────────────────────────────
    (re.compile(
        r"\b(isi\s+mark|isi\s+licence|isi\s+certification|crs\s+registration|"
        r"fmcs|foreign\s+manufacturer|compulsory\s+registration|eco\s+mark|"
        r"manak\s+online|manakonline|licence\s+fee|marking\s+fee|"
        r"apply\s+for\s+(bis|isi)|bis\s+(licence|license)|scheme\s+(i|ii|v|1|2|5)|"
        r"import.*india.*certif|voluntary\s+certif|mandatory\s+certif)\b",
        re.I,
    ), Intent.SCHEME_GUIDANCE, 0.92),

    # ── TECHNICAL_CLAUSE_QUERY ───────────────────────────────────────────────
    # ── TECHNICAL_CLAUSE_QUERY ───────────────────────────────────────────────
    (re.compile(
        r"\b(clauses?|section|permissible\s+limit|maximum\s+limit|minimum\s+(?:limit|strength)|"
        r"tolerance|specification|test\s+method|pH|turbidity|hardness|"
        r"tensile\s+strength|yield\s+strength|elongation|conductivity|"
        r"moisture\s+content|ash\s+content|calorific|viscosity|"
        r"mg/l|ppm|ntu|mpa|n/mm|kn|kpa|gpa|kwh|lux|db|rpm|"
        r"what\s+is\s+the\s+(limit|value|requirement|standard|specification)\s+for|"
        r"according\s+to\s+is\s+\d|as\s+per\s+is\s+\d|is\s+\d{3,6}\s+clause|"
        r"is\s+standard\s+requirements\s+and\s+technical\s+clauses)\b",
        re.I,
    ), Intent.TECHNICAL_CLAUSE_QUERY, 0.92),

    # ── PRODUCT_STANDARD_LOOKUP ──────────────────────────────────────────────
    (re.compile(
        r"\b(which\s+(is|indian)\s+standard|what\s+(is|standard|code)\s+(applies|covers|governs|for)|"
        r"applicable\s+(is|standard)|is\s+standard\s+for|"
        r"standard\s+for\s+(cement|steel|water|helmet|cable|pipe|toy|appliance|pressure\s+cooker|led|paint)|"
        r"find\s+(the\s+)?(is|standard|bis\s+standard)|"
        r"does\s+(this|my)\s+product\s+(need|require)\s+(bis|isi|is\s+standard))\b",
        re.I,
    ), Intent.PRODUCT_STANDARD_LOOKUP, 0.90),
]


def _classify_keywords(query: str) -> tuple[Intent, float]:
    """
    Stage-1 classification: O(n_rules) regex scan, no network call.

    Returns
    -------
    (intent, confidence)
        intent is AMBIGUOUS when no rule matched.
    """
    # Isolate just the user's current question for regex matching
    # to avoid false positives on words in the conversation history
    target_text = query
    if "[Current question]" in query:
        target_text = query.split("[Current question]")[-1]

    for pattern, intent, confidence in _KEYWORD_RULES:
        if pattern.search(target_text):
            logger.debug("Keyword match → %s (conf=%.2f)", intent.value, confidence)
            return intent, confidence

    # --- Conversational Continuations (Context-Aware Routing) ---
    # If the user is providing a short answer (e.g. just a city name) in response
    # to the Lab Finder's follow-up prompt, route back to LAB_SEARCH.
    if "To find a testing laboratory, please tell me" in query:
        logger.debug("Conversational continuation → LAB_SEARCH")
        return Intent.LAB_SEARCH, 0.85

    return Intent.AMBIGUOUS, 0.0


# =============================================================================
# Stage-2: LLM classifier (Gemini Flash, called only for ambiguous queries)
# =============================================================================

_LLM_CLASSIFICATION_PROMPT = """\
You are an intent classifier for the BIS (Bureau of Indian Standards) Knowledge Portal.
Classify the user query into EXACTLY ONE of these intents:

PRODUCT_STANDARD_LOOKUP  — User wants to know which IS standard applies to a product.
TECHNICAL_CLAUSE_QUERY   — User asks specific technical requirements (limits, parameters, test methods).
LAB_SEARCH               — User wants to find a lab to test a product.
SCHEME_GUIDANCE          — User wants certification or licensing guidance.
PROCESS_EXPLAINER        — User wants step-by-step process/procedure for getting certification (ISI, CRS, FMCS).
CONSUMER_HALLMARK        — User asks about HUID, gold hallmarking, or BIS complaints.
GENERAL_QUERY            — User asks a general question, greetings, or something not strictly related to finding a standard or lab.

Rules:
- If the query asks about a product, food item, or material (e.g., "tell me about dahi", "milk", "curd", "steel"), classify it as PRODUCT_STANDARD_LOOKUP.
- If it is a greeting or general knowledge, classify it as GENERAL_QUERY.
- Respond with a valid JSON object ONLY. No prose, no markdown.
- Format: {{"intent": "INTENT_NAME", "confidence": 0.XX, "reason": "one sentence"}}
- confidence must be a float between 0.0 and 1.0.

User query: "{query}"
"""


async def _classify_llm(query: str, llm: ChatOpenAI) -> tuple[Intent, float]:
    """
    Stage-2 classification: call Gemini Flash with a structured prompt.
    Falls back to PRODUCT_STANDARD_LOOKUP on parse failure.
    """
    prompt = _LLM_CLASSIFICATION_PROMPT.format(query=query.replace('"', "'"))
    try:
        response = await llm.ainvoke(prompt)
        text = response.content
        if isinstance(text, list):
            text = text[0].get("text", "") if isinstance(text[0], dict) else str(text[0])
        text = text.strip()

        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()

        parsed = json.loads(text)
        intent_str  = parsed.get("intent", "PRODUCT_STANDARD_LOOKUP")
        confidence  = float(parsed.get("confidence", 0.6))
        reason      = parsed.get("reason", "")

        intent = Intent[intent_str] if intent_str in Intent.__members__ else Intent.GENERAL_QUERY
        logger.debug("LLM classified → %s (conf=%.2f) reason=%r", intent.value, confidence, reason)
        return intent, confidence

    except Exception as exc:
        logger.warning("LLM classification failed (%s) — defaulting to GENERAL_QUERY", exc)
        return Intent.GENERAL_QUERY, 0.50

# =============================================================================
# Pipeline handlers  (one async method per intent)
# =============================================================================

def _db_session() -> Session:
    """Return a new SQLAlchemy session. Caller must close it."""
    return SessionLocal()


# ── Helper: extract city / product keyword from query ─────────────────────────

_LOCATION_PATTERN = re.compile(
    r"\b(delhi|new\s+delhi|mumbai|bombay|bangalore|bengaluru|chennai|madras|"
    r"kolkata|calcutta|pune|hyderabad|ahmedabad|jaipur|lucknow|surat|"
    r"bhopal|nagpur|patna|chandigarh|noida|gurugram|gurgaon|"
    r"andhra\s+pradesh|arunachal\s+pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s+pradesh|jharkhand|karnataka|kerala|madhya\s+pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s+nadu|telangana|tripura|uttar\s+pradesh|uttarakhand|west\s+bengal|"
    r"andaman|nicobar|dadra|nagar\s+haveli|daman|diu|lakshadweep|puducherry|ladakh|jammu|kashmir)\b",
    re.I,
)

_PRODUCT_TOKENS_RE = re.compile(
    r"\b(cement|steel|water|helmet|cable|pipe|toy|led|paint|"
    r"pressure\s+cooker|appliance|rubber|jute|glass|ceramic|"
    r"textile|leather|food|pharma|plastic|chemical|electronic|"
    r"solar|battery|inverter)\b",
    re.I,
)

def _extract_location(query: str) -> str | None:
    if "[Current question]" in query:
        query = query.split("[Current question]")[-1]
    m = _LOCATION_PATTERN.search(query)
    return m.group(1).title() if m else None

def _extract_product_keyword(query: str) -> str | None:
    if "[Current question]" in query:
        query = query.split("[Current question]")[-1]
    m = _PRODUCT_TOKENS_RE.search(query)
    return m.group(1).lower() if m else None


# ── Pipeline 1: PRODUCT_STANDARD_LOOKUP ──────────────────────────────────────

async def _handle_product_lookup(
    query: str,
    rag: RAGService,
) -> dict[str, Any]:
    """
    Retrieve IS standards applicable to the product mentioned in the query.

    Strategy
    --------
    Use RAG with a product-focused reformulation of the query.
    The system prompt is already citation-strict — response will include
    [Standard: IS XXXX, Clause: Y.Z] prefixes on every fact.
    """
    # Do not heavily reformulate the query for embedding search, as it dilutes the semantic
    # meaning for fastembed. We simply pass the raw query.
    result: RAGResponse = await rag.query(question=query, top_k=10)
    return {
        "type": "rag",
        "rag_response": result,
    }


# ── Pipeline 2: TECHNICAL_CLAUSE_QUERY ───────────────────────────────────────

async def _handle_technical_clause(
    query: str,
    rag: RAGService,
) -> dict[str, Any]:
    """
    Full RAG pipeline for precise technical requirements.

    Retrieves the most relevant IS clauses and generates a grounded,
    citation-enforced answer with the zero-hallucination fallback.
    """
    from app.services.rag_service import RAGResponse
    if query.strip().lower() == "is standard requirements and technical clauses":
        answer = "To help you with IS standard requirements, please tell me the name of the product or the IS standard number you are looking for."
        return {
            "type": "rag",
            "rag_response": RAGResponse(answer=answer, citations=[], retrieved_chunks=[], model_used="system", query=query, num_chunks_retrieved=0, fallback_triggered=True)
        }

    result: RAGResponse = await rag.query(question=query, top_k=8)
    return {
        "type": "rag",
        "rag_response": result,
    }


_LAB_SEARCH_EXTRACTION_PROMPT = """\
Extract the city/state and the specific product/material from the following query to search a laboratory database.
CRITICAL INSTRUCTIONS:
1. NORMALIZE the city or state name to its standard spelling (e.g., "tamilnadu" -> "Tamil Nadu", "delhi" -> "Delhi").
2. If a field is not mentioned, use actual JSON null (not the string "NULL").
Return a valid JSON object ONLY: {{"city": "City or State Name", "product": "Product Name"}}

Query: "{query}"
"""

_LAB_FILTER_PROMPT = """\
You are an expert at matching testing laboratories to products.
The user wants to test: "{product}"
Here are the available labs in their requested location:
{labs_json}

Analyze the "testing_scope" of each lab. Return a valid JSON list containing ONLY the integer IDs of the labs that are most capable of testing this product.
CRITICAL: You must be extremely generous to ensure the user gets a result. If no lab perfectly matches, select the closest industry match:
- For "LED" or electronics, select any lab testing "Electrical", "Cables", or "IT".
- For "Helmet", select any lab testing "Automotive", "Safety", or "Rubber".
- For any food/drink, select any lab testing "Food", "Beverages", "Chemical", or "Water".
Output ONLY a JSON list of integers, e.g. [1, 4, 7].
"""

async def _handle_lab_search(
    query: str,
    db: Session,
    llm: ChatOpenAI,
) -> dict[str, Any]:
    from sqlalchemy import or_, func as sqlfunc
    from app.services.rag_service import RAGResponse
    import json

    base_q = db.query(Laboratory).filter(Laboratory.is_active == True)

    city = None
    product = None
    
    # 1. Extract City and Product
    try:
        prompt = _LAB_SEARCH_EXTRACTION_PROMPT.format(query=query.replace('"', "'"))
        response = await llm.ainvoke(prompt)
        text = response.content.strip()
        if isinstance(text, list):
            text = text[0].get("text", "") if isinstance(text[0], dict) else str(text[0])
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
        parsed = json.loads(text)
        city = parsed.get("city")
        if city == "NULL" or city == "null": city = None
        product = parsed.get("product")
        if product == "NULL" or product == "null": product = None
        logger.debug("LLM extracted labs entities → city=%r product=%r", city, product)
    except Exception as exc:
        logger.warning("LLM lab extraction failed (%s) — defaulting to regex", exc)
        city    = _extract_location(query)
        product = _extract_product_keyword(query)

    if not city and not product:
        answer = "To find a testing laboratory, please tell me the product you want to test and your State or City."
        return {
            "type": "db_labs",
            "city_filter": None,
            "product_filter": None,
            "labs": [],
            "rag_response": RAGResponse(answer=answer, citations=[], retrieved_chunks=[], model_used="system", query=query, num_chunks_retrieved=0, fallback_triggered=False)
        }

    # 2. Fetch labs for the city (or all if no city)
    if city:
        candidate_labs = base_q.filter(Laboratory.city.ilike(f"%{city}%")).all()
        # If no labs in that exact city, expand search to state
        if not candidate_labs:
             candidate_labs = base_q.filter(Laboratory.state.ilike(f"%{city}%")).all()
    else:
        candidate_labs = base_q.limit(30).all()

    # 3. Use LLM to semantically filter the labs based on the product
    final_labs = candidate_labs
    if product and candidate_labs:
        try:
            labs_context = json.dumps([
                {"id": l.id, "name": l.name, "testing_scope": l.testing_scope} 
                for l in candidate_labs
            ], indent=2)
            
            filter_prompt = _LAB_FILTER_PROMPT.format(product=product, labs_json=labs_context)
            filter_resp = await llm.ainvoke(filter_prompt)
            filter_text = filter_resp.content.strip()
            if isinstance(filter_text, list):
                filter_text = filter_text[0].get("text", "") if isinstance(filter_text[0], dict) else str(filter_text[0])
            filter_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", filter_text, flags=re.DOTALL).strip()
            
            valid_ids = json.loads(filter_text)
            if isinstance(valid_ids, list):
                final_labs = [l for l in candidate_labs if l.id in valid_ids]
            logger.debug("LLM semantic filter chose labs: %r", valid_ids)
        except Exception as e:
            logger.warning(f"LLM semantic lab filter failed: {e}")
            # Fallback to simple ilike if LLM fails
            final_labs = [l for l in candidate_labs if product.lower() in (l.testing_scope or "").lower()]

    # Limit to top 10
    final_labs = final_labs[:10]

    if not final_labs:
        display_city = city or ""
        display_product = product or ""
        answer = f"No BIS-recognized labs found for '{display_product}' in '{display_city}'."
        answer = answer.replace(" for ''", "").replace(" in ''", "")
    else:
        display_city = city or ""
        display_product = product or ""
        answer = f"Found {len(final_labs)} BIS-recognized laboratories for '{display_product}' in '{display_city}'."
        answer = answer.replace(" for ''", "").replace(" in ''", "")

    return {
        "type": "db_labs",
        "city_filter": city,
        "product_filter": product,
        "labs": [
            {
                "id": l.id, "name": l.name, "city": l.city, "state": l.state, "pincode": l.pincode,
                "address": l.address, "phone": l.phone, "contact_email": l.contact_email,
                "website": l.website, "accreditations": l.accreditations, "testing_scope": l.testing_scope,
                "latitude": l.latitude, "longitude": l.longitude,
            } for l in final_labs
        ],
        "rag_response": RAGResponse(answer=answer, citations=[], retrieved_chunks=[], model_used="system", query=query, num_chunks_retrieved=0, fallback_triggered=False)
    }


# ── Pipeline 4: SCHEME_GUIDANCE ───────────────────────────────────────────────

async def _handle_scheme_guidance(
    query: str,
    db: Session,
    rag: RAGService,
) -> dict[str, Any]:
    """
    Hybrid pipeline: SQLite scheme lookup + optional RAG supplement.

    Step 1: Keyword-match the query against scheme_name, scheme_code,
            target_audience, applicable_products in `certification_schemes`.
    Step 2: If relevant IS clauses exist for the scheme, also run a
            focused RAG query so the caller gets both structured scheme
            metadata AND cited standard clause text.
    """
    from sqlalchemy import or_

    # --- Build keyword search terms from query ---
    tokens = set(re.findall(r"\b\w{4,}\b", query.lower()))

    # Fetch all active schemes, score by token overlap
    all_schemes: list[CertificationScheme] = (
        db.query(CertificationScheme)
          .filter(CertificationScheme.is_active == True)
          .all()
    )

    def _scheme_score(s: CertificationScheme) -> int:
        haystack = " ".join([
            (s.scheme_name or ""), (s.scheme_code or ""),
            (s.target_audience or ""), (s.applicable_products or ""),
            (s.description or ""),
        ]).lower()
        return sum(1 for t in tokens if t in haystack)

    scored = sorted(all_schemes, key=_scheme_score, reverse=True)
    top_schemes = [s for s in scored if _scheme_score(s) > 0][:3]

    scheme_dicts = [s.to_dict() for s in top_schemes]

    # Supplement with a RAG query for IS clause context
    rag_result: RAGResponse | None = None
    try:
        rag_result = await rag.query(
            question=query,
            top_k=5,
            is_strict=False,
        )
    except Exception as exc:
        logger.warning("Scheme RAG supplement failed: %s", exc)

    return {
        "type":     "hybrid_scheme",
        "schemes":  scheme_dicts,
        "rag_response": rag_result,
    }


# ── Pipeline 5: CONSUMER_HALLMARK ────────────────────────────────────────────

async def _handle_consumer_hallmark(
    query: str,
    db: Session,
    rag: RAGService,
) -> dict[str, Any]:
    """
    FAQ-first pipeline: search `consumer_faqs`, supplement with RAG if needed.

    Step 1: Keyword-score FAQs against the query.
    Step 2: If top FAQ score is < threshold, also run RAG for clause context
            (e.g. user asking about IS 1417 purity specifications).
    """
    from app.services.hallmark_service import verify_huid
    from app.services.rag_service import RAGResponse

    # ---------------------------------------------------------
    # HUID Verification Intercept
    # ---------------------------------------------------------
    huid_match = re.search(r"\b([A-Z0-9]{6})\b", query, re.IGNORECASE)
    is_verification_intent = bool(re.search(r"\b(verify|check|authentic)\b", query.lower())) and bool(re.search(r"\b(huid|gold|hallmark|jewel)\b", query.lower()))

    # Must contain at least one digit to be a valid HUID (prevents matching English words like "Scheme")
    if huid_match and any(c.isdigit() for c in huid_match.group(1)):
        huid_code = huid_match.group(1).upper()
        verification_data = verify_huid(huid_code, db)
        
        if verification_data:
            return {
                "type": "huid_verification",
                "faqs": [],
                "rag_response": None,
                "huid_verification": verification_data
            }
        else:
            return {
                "type": "huid_verification",
                "faqs": [],
                "rag_response": RAGResponse(
                    answer=f"The HUID code '{huid_code}' could not be verified in our records. Please ensure it is a valid 6-character alphanumeric code.",
                    citations=[],
                    retrieved_chunks=[],
                    model_used="system",
                    query=query,
                    num_chunks_retrieved=0,
                    fallback_triggered=True
                ),
                "huid_verification": None
            }
            
    elif is_verification_intent:
        return {
            "type": "huid_verification",
            "faqs": [],
            "rag_response": RAGResponse(
                answer="Please provide the 6-character alphanumeric HUID stamped on your jewelry (e.g., AB1234).",
                citations=[],
                retrieved_chunks=[],
                model_used="system",
                query=query,
                num_chunks_retrieved=0,
                fallback_triggered=True
            ),
            "huid_verification": None
        }

    stop_words = {"the", "and", "for", "that", "this", "with", "from", "your", "what", "how", "are", "but", "only", "you", "can", "will", "my", "is", "in", "on", "it", "to", "do", "of", "or"}
    tokens = set(re.findall(r"\b\w{3,}\b", query.lower())) - stop_words

    all_faqs: list[ConsumerFAQ] = (
        db.query(ConsumerFAQ)
          .filter(ConsumerFAQ.is_published == True)
          .order_by(ConsumerFAQ.sort_order)
          .all()
    )

    def _faq_score(f: ConsumerFAQ) -> int:
        haystack = " ".join([
            (f.topic or ""), (f.keywords or ""),
            (f.question or ""), (f.category or ""),
        ]).lower()
        return sum(1 for t in tokens if t in haystack)

    scored_faqs = sorted(all_faqs, key=_faq_score, reverse=True)
    
    # Filter FAQs strictly to avoid irrelevant cards on conversational queries.
    # Require at least 2 matching tokens for longer queries.
    top_score = _faq_score(scored_faqs[0]) if scored_faqs else 0
    required_score = 2 if len(tokens) >= 3 else 1
    top_faqs = [f for f in scored_faqs if _faq_score(f) >= required_score and _faq_score(f) >= (top_score * 0.6)][:3]

    # Supplement with RAG when technical clause detail is likely needed
    # (e.g. user asks about IS 1417 fineness limits)
    rag_result: RAGResponse | None = None
    top_score = _faq_score(top_faqs[0]) if top_faqs else 0
    needs_rag = top_score < 2 or any(
        kw in query.lower() for kw in ["limit", "clause", "standard", "is 1417", "is 2112", "specification"]
    )

    if needs_rag:
        try:
            rag_result = await rag.query(
                question=query, top_k=5, product_category=None, is_strict=False
            )
        except Exception as exc:
            logger.warning("Hallmark RAG supplement failed: %s", exc)

    return {
        "type": "hybrid_faq",
        "faqs": [
            {
                "id":               f.id,
                "topic":            f.topic,
                "category":         f.category,
                "question":         f.question,
                "resolution_steps": f.resolution_steps,
                "related_url":      f.related_url,
                "related_scheme":   f.related_scheme,
                "sort_order":       f.sort_order,
            }
            for f in top_faqs
        ],
        "rag_response": rag_result,
        "huid_verification": None
    }


# ── Pipeline 6: GENERAL_QUERY ────────────────────────────────────────────────

async def _handle_general_query(
    query: str,
    rag: RAGService,
) -> dict[str, Any]:
    """
    General query pipeline for greetings, random facts, and non-BIS queries.
    Uses RAG with is_strict=False to answer conversationally.
    """
    result: RAGResponse = await rag.query(question=query, top_k=2, is_strict=False)
    return {
        "type": "rag",
        "rag_response": result,
    }



# ── Pipeline 7: PROCESS_EXPLAINER ──────────────────────────────────────────────

async def _handle_process_explainer(
    query: str,
    llm: ChatOpenAI,
) -> dict[str, Any]:
    """
    Process Explainer pipeline.
    Step 1: Extract the scheme name from the query.
    Step 2: Fetch the JSON playbook using get_certification_steps tool.
    Step 3: Format the JSON into a Markdown checklist via LLM.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.services.tools import get_certification_steps
    import json

    # 1. Extract scheme
    extract_msg = SystemMessage(content=(
        "Extract the BIS certification scheme from the user query. "
        "Return ONLY the scheme name (e.g. 'ISI Mark', 'CRS', 'FMCS'). "
        "If unsure, return 'ISI Mark'."
    ))
    res = await llm.ainvoke([extract_msg, HumanMessage(content=query)])
    scheme = res.content.strip()

    # 2. Call tool
    tool_res = get_certification_steps.invoke({"scheme": scheme})

    # 3. Format as markdown
    format_msg = SystemMessage(content=(
        "You are an expert on BIS certifications. "
        "The user asked about the certification process. "
        "I will provide you with the official process JSON playbook for the requested scheme. "
        "Your task is to format this JSON into a clean, readable Markdown checklist. "
        "Use numbered lists (1., 2., 3.) or hyphen bullets (-). DO NOT use asterisks (*) for bullet points. "
        "Ensure there is always a blank empty line before starting any list. "
        "Use bold text for step titles, and include the portal_url at the end. "
        "Do not invent any steps. Only use the information provided in the JSON."
    ))
    final_res = await llm.ainvoke([format_msg, HumanMessage(content=f"User Query: {query}\n\nJSON Playbook: {json.dumps(tool_res)}")])

    return {
        "type": "process_explainer",
        "process_explainer": {
            "markdown": final_res.content,
            "raw_tool_output": tool_res
        }
    }


# =============================================================================
# QueryRouter  —  the public-facing orchestrator
# =============================================================================

class QueryRouter:
    """
    Routes user queries to the appropriate BIS knowledge pipeline.

    Parameters
    ----------
    rag_service:
        Initialised RAGService (used by 3 of the 5 pipelines).
    classifier_llm_model:
        Gemini model used only for Stage-2 (ambiguous) classification.
        Defaults to gemini-1.5-flash for minimal latency.
    google_api_key:
        Google AI API key; falls back to GOOGLE_API_KEY env var.

    Example
    -------
    >>> router = QueryRouter.from_env()
    >>> response = await router.route("Where can I test my PVC pipes in Delhi?")
    >>> print(response.intent)       # Intent.LAB_SEARCH
    >>> print(response.labs[:2])     # first 2 labs
    """

    def __init__(
        self,
        rag_service: RAGService,
        classifier_llm_model: str = "gemini-1.5-flash",
        google_api_key: str | None = None,
    ) -> None:
        self._rag = rag_service

        import os
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        google_key = google_api_key or os.environ.get("GOOGLE_API_KEY", "")
        
        # If the user put their OpenRouter key inside GOOGLE_API_KEY by mistake
        if not openrouter_key and google_key.startswith("sk-or"):
            openrouter_key = google_key

        if openrouter_key:
            from langchain_openai import ChatOpenAI
            self._classifier_llm = ChatOpenAI(
                model=classifier_llm_model,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.0,
                max_tokens=200,
            )
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._classifier_llm = ChatGoogleGenerativeAI(
                model=classifier_llm_model.replace("google/", ""),
                google_api_key=google_key,
                temperature=0.0,
                max_tokens=200,
            )

        logger.info(
            "QueryRouter ready — classifier_model=%s", classifier_llm_model
        )

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    async def classify(self, query: str) -> ClassificationResult:
        """
        Two-stage intent classification.

        1. Try fast keyword heuristics.
        2. Fall back to Gemini Flash only if ambiguous.

        Returns
        -------
        ClassificationResult
            Never returns Intent.AMBIGUOUS — always resolves to a real intent.
        """
        t0 = time.perf_counter()
        intent, confidence = _classify_keywords(query)
        stage = "keyword"

        if intent == Intent.AMBIGUOUS:
            intent, confidence = await _classify_llm(query, self._classifier_llm)
            stage = "llm"

        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Classified %r → %s (stage=%s, conf=%.2f, %.0f ms)",
            query[:60], intent.value, stage, confidence, latency_ms,
        )
        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            stage=stage,
            raw_query=query,
            latency_ms=latency_ms,
        )

    async def route(
        self,
        query: str,
        classification: ClassificationResult | None = None,
    ) -> RouterResponse:
        """
        Classify the query (if not pre-classified) and dispatch it to the
        appropriate specialised pipeline.

        Parameters
        ----------
        query:
            Raw user query string.
        classification:
            Optional pre-computed ClassificationResult.
            If None, classification is performed internally.

        Returns
        -------
        RouterResponse
            Unified response object; intent-specific fields are populated,
            others default to empty list / None.
        """
        if not query.strip():
            raise ValueError("Query must not be empty.")

        # 1. Classify (or reuse provided result)
        cls_result = classification or await self.classify(query)
        intent = cls_result.intent

        # 2. Dispatch to pipeline
        t0 = time.perf_counter()
        db: Session = _db_session()
        rag_response: RAGResponse | None = None
        labs:    list[dict] = []
        schemes: list[dict] = []
        faqs:    list[dict] = []
        huid_verification: dict[str, Any] | None = None
        process_explainer: dict[str, Any] | None = None
        error:   str | None = None

        try:
            if intent == Intent.PRODUCT_STANDARD_LOOKUP:
                payload = await _handle_product_lookup(query, self._rag)
                rag_response = payload["rag_response"]

            elif intent == Intent.TECHNICAL_CLAUSE_QUERY:
                payload = await _handle_technical_clause(query, self._rag)
                rag_response = payload["rag_response"]

            elif intent == Intent.LAB_SEARCH:
                payload = await _handle_lab_search(query, db, self._classifier_llm)
                labs = payload["labs"]
                rag_response = payload.get("rag_response")

            elif intent == Intent.SCHEME_GUIDANCE:
                payload = await _handle_scheme_guidance(query, db, self._rag)
                schemes      = payload["schemes"]
                rag_response = payload.get("rag_response")

            elif intent == Intent.CONSUMER_HALLMARK:
                payload = await _handle_consumer_hallmark(query, db, self._rag)
                faqs         = payload.get("faqs", [])
                rag_response = payload.get("rag_response")
                huid_verification = payload.get("huid_verification")

            elif intent == Intent.GENERAL_QUERY:
                payload = await _handle_general_query(query, self._rag)
                rag_response = payload["rag_response"]

            elif intent == Intent.PROCESS_EXPLAINER:
                payload = await _handle_process_explainer(query, self._classifier_llm)
                process_explainer = payload.get("process_explainer")

        except Exception as exc:
            logger.exception("Pipeline error for intent %s: %s", intent.value, exc)
            error = str(exc)

        finally:
            db.close()

        pipeline_latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Pipeline %s done in %.0f ms (error=%s)",
            intent.value, pipeline_latency_ms, error,
        )

        return RouterResponse(
            intent=intent,
            query=query,
            classification=cls_result,
            pipeline_latency_ms=pipeline_latency_ms,
            rag_response=rag_response,
            labs=labs,
            schemes=schemes,
            faqs=faqs,
            huid_verification=huid_verification,
            process_explainer=process_explainer,
            error=error,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Factory
    # ──────────────────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> "QueryRouter":
        """
        Build a QueryRouter from environment variables.

        Required env vars
        -----------------
        GOOGLE_API_KEY : Google AI API key.

        Optional env vars
        -----------------
        GEMINI_MODEL      : LLM for RAG (default: gemini-1.5-flash)
        QDRANT_HOST/PORT  : remote Qdrant (omit for local)
        QDRANT_PATH       : local Qdrant storage path
        """
        import os
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        rag_svc = RAGService.from_env()
        return cls(rag_service=rag_svc, classifier_llm_model=model)

"""
app/services/rag_service.py
───────────────────────────
Retrieval-Augmented Generation (RAG) service for BIS IS-standard queries.

Architecture
------------

  User Query
      │
      ▼
  EmbeddingService  ──►  text-embedding-004  ──►  768-dim query vector
      │
      ▼
  VectorService.search()  ──►  Qdrant COSINE ANN  ──►  top-K ISChunk dicts
      │
      ▼
  ContextBuilder         ──►  formats chunks into grounded prompt context
      │
      ▼
  RAGService._chain      ──►  LangChain LCEL chain
      │                         SystemPrompt + HumanPrompt
      │                         ChatGoogleGenerativeAI (Gemini 1.5 Pro/Flash)
      │
      ▼
  RAGResponse
      ├── answer          (str)  — grounded, cited response
      ├── citations       (list) — structured citation objects
      ├── retrieved_chunks(list) — raw Qdrant hits for transparency
      └── model_used      (str)

Grounding rules (enforced in system prompt)
-------------------------------------------
1. Answer ONLY using the retrieved IS-standard context — no external knowledge.
2. Every technical requirement or parameter MUST be prefixed with
   [Standard: IS XXXX, Clause: Y.Z].
3. If a specific clause or limit is absent from the retrieved context, output:
   "This specific parameter is not specified in the indexed standard clauses."
4. Do not paraphrase limits — quote them verbatim from the context.
5. Structured citation block appended after every response.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from fastembed import TextEmbedding

from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_MODEL_PRO:   str = "gemini-1.5-pro"
DEFAULT_MODEL_FLASH: str = "google/gemini-2.5-flash"
EMBEDDING_MODEL:     str = "BAAI/bge-small-en-v1.5"
DEFAULT_TOP_K:       int = 8
MAX_CONTEXT_CHARS:   int = 24_000   # ~6K tokens — stays within Gemini context window
SCORE_THRESHOLD:     float = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt  (the grounding contract)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """\
You are **BIS Standards Assistant**, an authoritative AI for the Bureau of Indian Standards (BIS).
Your role is to help manufacturers, importers, consumers, and compliance officers understand
Indian Standard (IS) requirements precisely and reliably.

RULE 1 — MANDATORY CITATION FORMAT
Every technical requirement, permissible limit, test method, or parameter
you state MUST begin with the citation tag:

    [Standard: IS XXXX, Clause: Y.Z]

Replace XXXX with the actual standard number and Y.Z with the actual
clause or sub-clause number from the context. Never fabricate or guess
clause numbers. If the clause number is not available in the context,
use:  [Standard: IS XXXX, Clause: unknown]
"""

_STRICT_RULES = """\
GROUNDING CONTRACT (STRICT MODE):
1. CONTEXT-ONLY: You MUST answer exclusively using the <context> block provided below. Do NOT use any external knowledge about IS standards or limits.
2. VERBATIM LIMITS: Quote numerical limits verbatim from the context. Do not paraphrase.
3. ZERO-HALLUCINATION FALLBACK: If the user explicitly asks for a numerical limit, tolerance, or parameter, and the exact value is missing from the context, you MUST respond exactly with:
"This specific parameter is not specified in the indexed standard clauses."
4. If the query is general (e.g. "what are the standards for helmet"), provide a comprehensive summary of the retrieved context without using the fallback phrase.
5. FORMATTING: Use numbered lists (1., 2.) or hyphens (-) for lists. DO NOT use asterisks (*) for bullet points. Ensure a blank line before any list.
"""

_GENERAL_RULES = """\
GROUNDING CONTRACT (GENERAL MODE):
1. USE KNOWLEDGE: You are answering a general consumer or scheme inquiry. You may use your internal knowledge about the Bureau of Indian Standards, Hallmarking rules, HUID, and consumer rights to answer the question.
2. USE CONTEXT IF HELPFUL: A <context> block may be provided below. If it contains relevant details, incorporate them into your answer and cite them. 
3. NO FALLBACKS: If the context is irrelevant or empty, simply answer the question thoroughly using your internal knowledge. Do NOT say "This specific parameter is not specified...".
4. STAY ON TOPIC: If the user's question is completely unrelated to BIS, Standards, Certification, or Hallmarking, politely decline to answer.
5. FORMATTING: Use numbered lists (1., 2.) or hyphens (-) for lists. DO NOT use asterisks (*) for bullet points. Ensure a blank line before any list.
"""

_PROMPT_SUFFIX = """\
RULE 7 — OUT-OF-SCOPE QUERIES
If the user's question is entirely unrelated to Indian Standards, BIS
certification, product compliance, or consumer protection, respond:
    "I am specialised in BIS Indian Standards and cannot assist with
     questions outside this domain."

══════════════════════════════════════════════════════════════════════
CONTEXT BLOCK (retrieved from indexed IS standards)
══════════════════════════════════════════════════════════════════════

{context}

══════════════════════════════════════════════════════════════════════
"""

_HUMAN_PROMPT_TEMPLATE = """\
Query: {question}

Instructions:
- Cite every technical fact with [Standard: IS XXXX, Clause: Y.Z].
- Append a ## Sources Used section after your answer.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Citation:
    """A single extracted citation from the RAG response."""
    standard_code: str
    clause_number: str
    clause_title: str
    page_number: int
    score: float
    excerpt: str


@dataclass
class RAGResponse:
    """Complete response returned by RAGService.query()."""
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[dict[str, Any]]
    model_used: str
    query: str
    num_chunks_retrieved: int
    fallback_triggered: bool = False   # True if zero-hallucination fallback was used


# ─────────────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_context(chunks: list[dict[str, Any]], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Format Qdrant search results into a structured context block for the LLM.

    Each chunk is rendered as a clearly delimited block containing its
    standard code, clause identifier, title, page number, and text content.
    Chunks are ordered by score (highest first) and truncated to stay within
    the character budget.

    Parameters
    ----------
    chunks:
        List of dicts as returned by VectorService.search() — must have keys:
        standard_code, clause_number, clause_title, text, page_number, score.
    max_chars:
        Maximum total character budget for the context block.

    Returns
    -------
    str
        Formatted context string ready for injection into the system prompt.
    """
    if not chunks:
        return "[No relevant IS standard clauses were found in the indexed corpus.]"

    # Sort by score descending (should already be sorted by Qdrant, but be safe)
    sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)

    parts: list[str] = []
    total_chars = 0

    for idx, chunk in enumerate(sorted_chunks, start=1):
        standard = chunk.get("standard_code", "Unknown Standard")
        clause   = chunk.get("clause_number",  "?")
        title    = chunk.get("clause_title",   "")
        text     = chunk.get("text",           "").strip()
        page     = chunk.get("page_number",    0)
        score    = chunk.get("score",          0.0)

        block = (
            f"--- CHUNK {idx} ---\n"
            f"Standard  : {standard}\n"
            f"Clause    : {clause}"
            + (f" — {title}" if title else "") + "\n"
            f"Page      : {page}\n"
            f"Relevance : {score:.3f}\n"
            f"\n{text}\n"
            f"--- END CHUNK {idx} ---\n"
        )

        if total_chars + len(block) > max_chars:
            logger.debug(
                "Context budget exhausted at chunk %d (%d/%d chars). Stopping.",
                idx, total_chars, max_chars,
            )
            break

        parts.append(block)
        total_chars += len(block)

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Citation extractor
# ─────────────────────────────────────────────────────────────────────────────

# Matches: [Standard: IS 10500, Clause: 4.2.1]  or  [Standard: IS 10500:2012, Clause: 4.2]
_CITATION_RE = re.compile(
    r"\[Standard:\s*(IS\s*[\d]+(?:[:/\-]\S*)?),\s*Clause:\s*([\d\.]+|unknown)\]",
    re.IGNORECASE,
)


def _extract_citations(
    answer: str,
    chunks: list[dict[str, Any]],
) -> list[Citation]:
    """
    Parse [Standard: IS XXXX, Clause: Y.Z] tags from the model's answer
    and cross-reference with the retrieved chunks to build Citation objects.

    Parameters
    ----------
    answer:
        The raw text response from the LLM.
    chunks:
        Retrieved Qdrant chunks (same list passed to context builder).

    Returns
    -------
    list[Citation]
        Deduplicated, ordered list of citations mentioned in the answer.
    """
    seen: set[tuple[str, str]] = set()
    citations: list[Citation] = []

    for m in _CITATION_RE.finditer(answer):
        standard_raw = m.group(1).strip()
        clause_raw   = m.group(2).strip()

        key = (standard_raw, clause_raw)
        if key in seen:
            continue
        seen.add(key)

        # Find the best-matching chunk to pull title, page, score, excerpt
        matched_chunk: dict[str, Any] = {}
        best_score = -1.0

        for chunk in chunks:
            chunk_std    = chunk.get("standard_code", "")
            chunk_clause = chunk.get("clause_number",  "")

            # Normalise comparison (strip spaces around colons)
            std_match    = re.sub(r"\s*:\s*", ":", standard_raw) in re.sub(r"\s*:\s*", ":", chunk_std)
            clause_match = clause_raw == chunk_clause or chunk_clause.startswith(clause_raw)

            if std_match and clause_match:
                s = chunk.get("score", 0.0)
                if s > best_score:
                    best_score    = s
                    matched_chunk = chunk

        # Fall back to any chunk from the same standard if no clause match
        if not matched_chunk:
            for chunk in chunks:
                if re.sub(r"\s*:\s*", ":", standard_raw) in re.sub(r"\s*:\s*", ":", chunk.get("standard_code", "")):
                    s = chunk.get("score", 0.0)
                    if s > best_score:
                        best_score    = s
                        matched_chunk = chunk

        text    = matched_chunk.get("text", "")
        excerpt = text[:300] + "…" if len(text) > 300 else text

        citations.append(
            Citation(
                standard_code=standard_raw,
                clause_number=clause_raw,
                clause_title=matched_chunk.get("clause_title", ""),
                page_number=matched_chunk.get("page_number", 0),
                score=best_score if best_score > 0 else 0.0,
                excerpt=excerpt,
            )
        )

    return citations


# ─────────────────────────────────────────────────────────────────────────────
# RAGService
# ─────────────────────────────────────────────────────────────────────────────

class RAGService:
    """
    Retrieval-Augmented Generation service for BIS IS-standard queries.

    Uses LangChain LCEL chains with Google Gemini (1.5 Pro or Flash)
    as the language model, backed by Qdrant vector search via VectorService.

    Parameters
    ----------
    vector_service:
        An initialised VectorService instance (Qdrant client wrapper).
    model_name:
        Gemini model to use. Options:
        - "gemini-1.5-pro"   (higher quality, slower, costlier)
        - "gemini-1.5-flash" (faster, cheaper, still high quality)
        Defaults to the GEMINI_MODEL env var or "gemini-1.5-flash".
    temperature:
        LLM temperature. Default 0.0 for maximum determinism / factuality.
    top_k:
        Number of vector search results to retrieve per query.
    google_api_key:
        Google AI API key. Falls back to GOOGLE_API_KEY env var.

    Example
    -------
    >>> svc = RAGService(vector_service=VectorService.from_env())
    >>> resp = await svc.query("What is the permissible turbidity limit in IS 10500?")
    >>> print(resp.answer)
    [Standard: IS 10500, Clause: 4.1] The permissible limit for turbidity ...
    """

    def __init__(
        self,
        vector_service: VectorService,
        model_name: str | None = None,
        temperature: float = 0.0,
        top_k: int = DEFAULT_TOP_K,
        google_api_key: str | None = None,
    ) -> None:
        self._vector_svc = vector_service
        self._top_k      = top_k

        api_key = google_api_key or os.environ.get("OPENROUTER_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Set it as an environment variable or pass google_api_key=..."
            )

        self._model_name = (
            model_name
            or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL_FLASH)
        )

        # ── Embedding model (for query vectorisation) ─────────────────────
        self._embeddings = TextEmbedding(model_name=EMBEDDING_MODEL)

        # ── LLM ──────────────────────────────────────────────────────────
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        google_key = os.environ.get("GOOGLE_API_KEY", "")
        
        # If the user put their OpenRouter key inside GOOGLE_API_KEY by mistake
        if not openrouter_key and google_key.startswith("sk-or"):
            openrouter_key = google_key

        if openrouter_key:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self._model_name,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=600,
            )
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(
                model=self._model_name.replace("google/", ""),
                google_api_key=google_key,
                temperature=temperature,
                max_tokens=600,
            )

        # ── Prompt template ───────────────────────────────────────────────
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT_BASE + _GENERAL_RULES + _PROMPT_SUFFIX),
            ("human",  "Context:\n<context>\n{context}\n</context>\n\n" + _HUMAN_PROMPT_TEMPLATE),
        ])

        # ── LCEL chain: prompt | llm | output_parser ──────────────────────
        self._chain = self._prompt | self._llm | StrOutputParser()

        logger.info(
            "RAGService initialised: model=%s, top_k=%d, embedding=%s",
            self._model_name, self._top_k, EMBEDDING_MODEL,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Core query method (async)
    # ──────────────────────────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        standard_code: str | None = None,
        product_category: str | None = None,
        top_k: int | None = None,
        is_strict: bool = True,
    ) -> RAGResponse:
        """
        Full async RAG pipeline: embed query → retrieve chunks → generate answer.

        Parameters
        ----------
        question:
            The user's natural language question.
        standard_code:
            Optional filter to restrict retrieval to a specific IS standard
            e.g. "IS 10500:2012".
        product_category:
            Optional filter by product category e.g. "Drinking Water".
        top_k:
            Override the instance-level top_k for this query only.

        Returns
        -------
        RAGResponse
            Structured response with answer, citations, and retrieved chunks.
        """
        if not question.strip():
            raise ValueError("Question must not be empty.")

        k = top_k or self._top_k
        logger.info("RAG query: %r (filter: std=%s, cat=%s, k=%d)",
                    question, standard_code, product_category, k)

        # 1. Embed the query ─────────────────────────────────────────────
        query_vector: list[float] = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(next(self._embeddings.embed([question]))),
        )

        # 2. Retrieve from Qdrant ────────────────────────────────────────
        chunks: list[dict[str, Any]] = self._vector_svc.search(
            query_vector=query_vector,
            top_k=k,
            standard_code=standard_code,
            product_category=product_category,
            score_threshold=SCORE_THRESHOLD,
        )
        # 3. Build grounded context ──────────────────────────────────────
        context = _build_context(chunks)

        if not context.strip() or context == "[No relevant IS standard clauses were found in the indexed corpus.]":
            logger.warning("No context available after threshold filtering")
            if is_strict:
                return RAGResponse(
                    answer="This specific parameter is not specified in the indexed standard clauses.",
                    citations=[],
                    retrieved_chunks=chunks,
                    model_used=self._model_name,
                    query=question,
                    num_chunks_retrieved=len(chunks),
                    fallback_triggered=True,
                )

        # 4. Generate answer via LangChain chain ─────────────────────────
        system_prompt = _SYSTEM_PROMPT_BASE + (_STRICT_RULES if is_strict else _GENERAL_RULES) + _PROMPT_SUFFIX
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Context:\n<context>\n{context}\n</context>\n\n" + _HUMAN_PROMPT_TEMPLATE)
        ])
        
        chain = prompt | self._llm | StrOutputParser()

        answer: str = await chain.ainvoke({
            "context":  context,
            "question": question,
        })

        # 5. Extract structured citations ────────────────────────────────
        citations = _extract_citations(answer, chunks)

        # 6. Detect fallback triggers ────────────────────────────────────
        fallback_phrase = "not specified in the indexed standard clauses"
        fallback_triggered = fallback_phrase.lower() in answer.lower()

        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks=chunks,
            model_used=self._model_name,
            query=question,
            num_chunks_retrieved=len(chunks),
            fallback_triggered=fallback_triggered,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Synchronous convenience wrapper
    # ──────────────────────────────────────────────────────────────────────

    def query_sync(
        self,
        question: str,
        standard_code: str | None = None,
        product_category: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Synchronous wrapper around :meth:`query`.

        Prefer the async version in FastAPI endpoints; use this only
        from scripts, tests, or CLI tools.
        """
        return asyncio.run(
            self.query(question, standard_code, product_category, top_k)
        )

    # ──────────────────────────────────────────────────────────────────────
    # Streaming variant (yields text chunks)
    # ──────────────────────────────────────────────────────────────────────

    async def stream(
        self,
        question: str,
        standard_code: str | None = None,
        product_category: str | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Async generator that streams the LLM response token-by-token.

        Usage in FastAPI (Server-Sent Events)::

            from fastapi.responses import StreamingResponse

            @router.get("/rag/stream")
            async def rag_stream(q: str):
                async def generate():
                    async for token in rag_service.stream(q):
                        yield f"data: {token}\\n\\n"
                return StreamingResponse(generate(), media_type="text/event-stream")

        Retrieval (steps 1–3) happens before streaming begins.
        The context grounding contract is identical to :meth:`query`.

        Yields
        ------
        str
            Individual text tokens/chunks as they are generated by Gemini.
        """
        if not question.strip():
            raise ValueError("Question must not be empty.")

        k = top_k or self._top_k

        # Retrieve synchronously (runs in executor to avoid blocking event loop)
        query_vector: list[float] = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(next(self._embeddings.embed([question]))),
        )
        chunks = self._vector_svc.search(
            query_vector=query_vector,
            top_k=k,
            standard_code=standard_code,
            product_category=product_category,
            score_threshold=SCORE_THRESHOLD,
        )
        context = _build_context(chunks)

        # Stream from Gemini via LCEL .astream()
        async for token in self._chain.astream({
            "context":  context,
            "question": question,
        }):
            yield token

    # ──────────────────────────────────────────────────────────────────────
    # Utility: re-rank retrieved chunks by a secondary heuristic
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def rerank_chunks(
        chunks: list[dict[str, Any]],
        question: str,
    ) -> list[dict[str, Any]]:
        """
        Simple lexical re-ranking on top of vector search scores.

        Boosts chunks whose clause title or text contain exact query terms,
        giving them a higher effective rank without a second model call.

        Parameters
        ----------
        chunks:
            Qdrant search results.
        question:
            Original user query.

        Returns
        -------
        list[dict]
            Re-ranked chunks (best first).
        """
        query_tokens = set(re.findall(r"\b\w{3,}\b", question.lower()))

        def _boost(chunk: dict) -> float:
            base  = chunk.get("score", 0.0)
            text  = (chunk.get("text", "") + " " + chunk.get("clause_title", "")).lower()
            hits  = sum(1 for t in query_tokens if t in text)
            # Each keyword hit adds 0.02 to the effective score
            return base + hits * 0.02

        return sorted(chunks, key=_boost, reverse=True)

    # ──────────────────────────────────────────────────────────────────────
    # Factory — build from environment variables
    # ──────────────────────────────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        model_name: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> "RAGService":
        """
        Construct a RAGService from environment variables.

        Environment variables
        ---------------------
        GOOGLE_API_KEY : Google AI API key (required)
        GEMINI_MODEL   : Model to use (default: gemini-1.5-flash)
        QDRANT_HOST    : Remote Qdrant host (omit for local)
        QDRANT_PORT    : Remote Qdrant port (default 6333)
        QDRANT_PATH    : Local storage path (default data/qdrant_storage)
        """
        from app.services.vector_service import get_vector_service
        vector_svc = get_vector_service()
        return cls(
            vector_service=vector_svc,
            model_name=model_name,
            top_k=top_k,
        )
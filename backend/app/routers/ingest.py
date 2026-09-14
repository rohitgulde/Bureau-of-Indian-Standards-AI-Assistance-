"""
app/routers/ingest.py
─────────────────────
PDF upload + ingestion router for the BIS Knowledge Portal.

Endpoints
---------
POST /api/ingest/upload
    Accept one or more PDF files via multipart/form-data.
    Saves them to data/raw_pdfs/, then runs the full parse→embed→upsert
    pipeline and streams progress back as Server-Sent Events (SSE).

GET /api/ingest/status
    Returns current Qdrant collection stats (total vectors, collection name).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])

# Resolve paths relative to the backend/ root
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PDF_DIR = _BACKEND_ROOT / "data" / "raw_pdfs"
_PDF_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "500"))

_CATEGORY_HINTS: dict[str, str] = {
    "10500": "Drinking Water",
    "9873":  "Safety of Toys",
    "15885": "LED Drivers",
    "2062":  "Structural Steel",
    "12778": "Helmets",
    "1786":  "High Strength Deformed Steel Bars",
    "432":   "Mild Steel",
    "3696":  "Safety Matches",
    "1844":  "Rubber Hoses",
    "8183":  "Bonded Mineral Fibre",
    "14846": "Household LPG Regulators",
    "4246":  "Pressure Cookers",
    "302":   "Household Electrical Appliances",
    "616":   "Incandescent Lamps",
    "694":   "PVC Insulated Cables",
    "9431":  "Jute Sacking Bags",
    "1077":  "Common Burnt Clay Bricks",
    "9617":  "Fermented Milk",
    "16102": "LED Lamps",
    "1417":  "Gold Jewellery",
    "4250":  "Electric Food Mixers",
    "14543": "Packaged Drinking Water",
}


def _infer_category(standard_code: str, filename: str = "") -> str:
    # First try by standard code matching
    m = re.search(r"IS\s*([\d]+)", standard_code, re.IGNORECASE)
    if m and m.group(1) in _CATEGORY_HINTS:
        return _CATEGORY_HINTS[m.group(1)]
        
    # Then try by filename keyword matching
    filename_lower = filename.lower()
    if "helmet" in filename_lower:
        return "Helmets"
    elif "toy" in filename_lower:
        return "Safety of Toys"
    elif "water" in filename_lower:
        return "Drinking Water"
        
    return standard_code or "General Product"


def _build_embed_text(chunk: dict) -> str:
    parts: list[str] = []
    if chunk.get("standard_code"):
        parts.append(chunk["standard_code"])
    if chunk.get("clause_number") and chunk.get("clause_title"):
        parts.append(f"§ {chunk['clause_number']} {chunk['clause_title']}")
    elif chunk.get("clause_number"):
        parts.append(f"§ {chunk['clause_number']}")
    if chunk.get("content"):
        parts.append(chunk["content"])
    return "\n".join(parts)


async def _stream_ingest(pdf_paths: list[Path]) -> AsyncIterator[str]:
    """
    Async generator that runs the full ingestion pipeline for the given PDFs
    and yields SSE-formatted progress messages.
    """

    def sse(msg: str) -> str:
        return f"data: {msg}\n\n"

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        yield sse("ERROR: GOOGLE_API_KEY is not set in .env")
        return

    # ── Lazy imports (avoid slow startup cost at module level) ────────────
    from fastembed import TextEmbedding
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import get_vector_service

    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    vector_svc = get_vector_service()

    total_files = len(pdf_paths)
    total_parsed = 0
    total_upserted = 0

    yield sse(f"🚀 Starting ingestion of {total_files} PDF(s)…")

    for file_idx, pdf_path in enumerate(pdf_paths, start=1):
        yield sse(f"📄 [{file_idx}/{total_files}] Parsing: {pdf_path.name}")

        # 1. Parse PDF
        try:
            chunks = await asyncio.get_event_loop().run_in_executor(
                None, parse_is_document, pdf_path
            )
        except Exception as exc:
            yield sse(f"❌ Failed to parse {pdf_path.name}: {exc}")
            continue

        if not chunks:
            yield sse(f"⚠️  No clauses extracted from {pdf_path.name} — skipping.")
            continue

        yield sse(f"   ✔ Extracted {len(chunks)} clause chunks")
        total_parsed += len(chunks)

        # 2. Annotate
        standard_code = chunks[0].get("standard_code", "") if chunks else ""
        product_category = _infer_category(standard_code, pdf_path.name)
        for chunk in chunks:
            chunk["product_category"] = product_category
            chunk["source_file"] = pdf_path.name

        # 3. Embed in batches
        embed_texts = [_build_embed_text(c) for c in chunks]
        all_vectors: list[list[float]] = []
        num_batches = (len(embed_texts) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE

        for batch_idx in range(num_batches):
            start = batch_idx * EMBED_BATCH_SIZE
            batch = embed_texts[start: start + EMBED_BATCH_SIZE]
            yield sse(
                f"   🔢 Embedding batch {batch_idx + 1}/{num_batches} "
                f"({len(batch)} texts)…"
            )
            try:
                # FastEmbed runs synchronously and fast
                embeddings = list(embedding_model.embed(batch))
                all_vectors.extend([list(emb) for emb in embeddings])
            except Exception as exc:
                yield sse(f"   ⚠️  Embedding error on batch {batch_idx + 1}: {exc}")
                all_vectors.extend([[0.0] * 384] * len(batch))

        # 4. Upsert
        yield sse(f"   💾 Storing {len(all_vectors)} vectors in Qdrant…")
        try:
            upserted = await asyncio.get_event_loop().run_in_executor(
                None, lambda: vector_svc.upsert_chunks(chunks, all_vectors)
            )
            total_upserted += upserted
            yield sse(f"   ✅ {pdf_path.name} → {upserted} vectors stored [{product_category}]")
        except Exception as exc:
            yield sse(f"   ❌ Upsert failed for {pdf_path.name}: {exc}")

    # ── Final summary ─────────────────────────────────────────────────────
    try:
        info = vector_svc.get_collection_info()
        total_in_db = info.get("points_count", "?")
    except Exception:
        total_in_db = "?"

    yield sse("─" * 48)
    yield sse(f"✅ Ingestion complete!")
    yield sse(f"   Files processed : {total_files}")
    yield sse(f"   Clauses parsed  : {total_parsed}")
    yield sse(f"   Vectors stored  : {total_upserted}")
    yield sse(f"   Total in DB     : {total_in_db}")
    yield sse("DONE")  # sentinel for the frontend


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_and_ingest(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF files and ingest them into the vector DB instantly.
    Streams progress back to the client via SSE.
    """
    pdf_paths: list[Path] = []

    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            continue
        dest = _PDF_DIR / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        pdf_paths.append(dest)
        logger.info("Saved uploaded PDF: %s (%d bytes)", dest.name, len(content))

    if not pdf_paths:
        return JSONResponse(
            status_code=400,
            content={"error": "No valid PDF files received."},
        )

    return StreamingResponse(_stream_ingest(pdf_paths), media_type="text/event-stream")

@router.get("/status")
async def ingest_status():
    """Return current Qdrant collection stats."""
    try:
        from app.services.vector_service import get_vector_service
        svc = get_vector_service()
        info = svc.get_collection_info()
        return {
            "collection": info.get("name", "bis_standards"),
            "total_vectors": info.get("points_count", 0),
            "status": "ready",
        }
    except Exception as exc:
        return {
            "collection": "bis_standards",
            "total_vectors": 0,
            "status": f"error: {exc}",
        }

@router.get("/sample")
async def ingest_sample():
    """Return a few sample chunks from the database for demonstration."""
    try:
        from app.services.vector_service import get_vector_service, COLLECTION_NAME
        svc = get_vector_service()
        response = svc._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=3,
            with_payload=True
        )
        
        samples = []
        for point in response[0]:
            payload = point.payload
            content = payload.get('text', '')
            if len(content) > 150:
                content = content[:147] + "..."
                
            samples.append({
                "standard_code": payload.get('standard_code', 'N/A'),
                "clause_number": payload.get('clause_number', 'N/A'),
                "source_file": payload.get('source_file', 'N/A'),
                "content_preview": content
            })
            
        return {"samples": samples}
    except Exception as exc:
        return {"error": str(exc)}

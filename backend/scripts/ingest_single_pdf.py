"""
scripts/ingest_single_pdf.py
Ingest a single IS-standard PDF into the Qdrant vector DB.

Usage:
    python scripts/ingest_single_pdf.py <path-to-pdf>

Example:
    python scripts/ingest_single_pdf.py data/raw_pdfs/IS9617_2023.pdf
"""

from __future__ import annotations

import os
import re
import sys
import time
import logging
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure backend/ is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env", override=False)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_single")

# -- Category hints --------------------------------------------------------
CATEGORY_HINTS: dict[str, str] = {
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
}


def infer_category(standard_code: str) -> str:
    m = re.search(r"IS\s*([\d]+)", standard_code, re.IGNORECASE)
    if m:
        return CATEGORY_HINTS.get(m.group(1), standard_code)
    return standard_code


def build_embed_text(chunk: dict) -> str:
    parts: list[str] = []
    if chunk.get("standard_code"):
        parts.append(chunk["standard_code"])
    if chunk.get("clause_number") and chunk.get("clause_title"):
        parts.append(f"S {chunk['clause_number']} {chunk['clause_title']}")
    elif chunk.get("clause_number"):
        parts.append(f"S {chunk['clause_number']}")
    if chunk.get("content"):
        parts.append(chunk["content"])
    return "\n".join(parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_single_pdf.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.is_absolute():
        pdf_path = BACKEND_ROOT / pdf_path
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(1)

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY is not set in .env")
        sys.exit(1)

    embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "50"))
    embedding_model = "BAAI/bge-small-en-v1.5"

    # -- Imports -----------------------------------------------------------
    from fastembed import TextEmbedding
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import VectorService

    gemini_client = TextEmbedding(model_name=embedding_model)
    vector_svc = VectorService.from_env()

    # -- 1. Parse ----------------------------------------------------------
    print(f"\n[PARSE] Parsing: {pdf_path.name}")
    t0 = time.time()
    chunks = parse_is_document(pdf_path)
    print(f"   [OK] Extracted {len(chunks)} clause chunks  ({time.time()-t0:.1f}s)")

    if not chunks:
        print("[WARN] No clauses extracted -- aborting.")
        sys.exit(1)

    # -- 2. Annotate -------------------------------------------------------
    standard_code = chunks[0].get("standard_code", "") if chunks else ""
    product_category = infer_category(standard_code)
    print(f"   Standard code : {standard_code}")
    print(f"   Category      : {product_category}")

    for chunk in chunks:
        chunk["product_category"] = product_category
        chunk["source_file"] = pdf_path.name

    # -- 3. Embed ----------------------------------------------------------
    embed_texts = [build_embed_text(c) for c in chunks]
    all_vectors: list[list[float]] = []
    num_batches = (len(embed_texts) + embed_batch_size - 1) // embed_batch_size

    print(f"\n[EMBED] Embedding {len(embed_texts)} texts in {num_batches} batch(es)...")
    for batch_idx in range(num_batches):
        start = batch_idx * embed_batch_size
        batch = embed_texts[start: start + embed_batch_size]
        print(f"   Batch {batch_idx+1}/{num_batches} ({len(batch)} texts)...", end=" ", flush=True)
        try:
            embeddings = list(gemini_client.embed(batch))
            all_vectors.extend([list(emb) for emb in embeddings])
            print("[OK]")
        except Exception as exc:
            print(f"[WARN] Error: {exc}")
            all_vectors.extend([[0.0] * 384] * len(batch))

    # -- 4. Upsert ---------------------------------------------------------
    print(f"\n[STORE] Storing {len(all_vectors)} vectors in Qdrant...")
    upserted = vector_svc.upsert_chunks(chunks, all_vectors)

    # -- 5. Summary --------------------------------------------------------
    info = vector_svc.get_collection_info()
    total_in_db = info.get("points_count", "?")

    print(f"\n{'=' * 48}")
    print(f"[DONE] Ingestion complete!")
    print(f"   Clauses parsed  : {len(chunks)}")
    print(f"   Vectors stored  : {upserted}")
    print(f"   Total in DB     : {total_in_db}")
    print(f"{'=' * 48}\n")


if __name__ == "__main__":
    main()

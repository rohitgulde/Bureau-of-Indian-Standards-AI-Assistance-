"""
scripts/ingest_standards.py
────────────────────────────
Batch ingestion pipeline for Indian Standard (IS) PDF documents.

Pipeline stages
---------------
1. Scan  ``data/raw_pdfs/`` for PDF files.
2. Parse each PDF via ``app.utils.pdf_parser.parse_is_document``.
3. Embed clause chunks with Google Gemini ``text-embedding-004`` (768-dim).
4. Upsert vectors + metadata into Qdrant via ``app.services.vector_service``.

Usage
-----
    # From the backend/ root (venv activated)
    python -m scripts.ingest_standards

    # Override PDF directory
    python -m scripts.ingest_standards --pdf-dir path/to/pdfs

    # Wipe existing collection before ingesting
    python -m scripts.ingest_standards --recreate

    # Dry-run: parse + embed without writing to Qdrant
    python -m scripts.ingest_standards --dry-run

Environment variables
---------------------
GOOGLE_API_KEY      : (required) Google AI API key for Gemini embeddings
QDRANT_HOST         : optional remote Qdrant host (omit for local in-process)
QDRANT_PORT         : optional port (default 6333)
QDRANT_PATH         : local storage path (default data/qdrant_storage)
EMBED_BATCH_SIZE    : how many texts to embed in one API call (default 50)
INGEST_BATCH_SIZE   : Qdrant upsert batch size (default 256)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Allow running as  python -m scripts.ingest_standards  from backend/
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

load_dotenv(_BACKEND_ROOT / ".env", override=True)

from fastembed import TextEmbedding

from app.utils.pdf_parser import parse_is_document
from app.services.vector_service import VectorService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
DEFAULT_PDF_DIR: str = "data/raw_pdfs"
EMBED_BATCH_SIZE: int = int(os.getenv("EMBED_BATCH_SIZE", "50"))

# Category heuristics: keyword → product_category label
# Extend this dict as new IS documents are added.
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
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_product_category(standard_code: str) -> str:
    """
    Derive a human-readable product category from the IS number.

    Looks up the IS number against the ``_CATEGORY_HINTS`` dict.
    Falls back to the raw standard_code string if no hint is found.

    Parameters
    ----------
    standard_code : str
        Normalised code, e.g. "IS 10500:2012".
    """
    import re
    m = re.search(r"IS\s+([\d]+)", standard_code, re.IGNORECASE)
    if m:
        is_number = m.group(1)
        return _CATEGORY_HINTS.get(is_number, standard_code)
    return standard_code


def _build_embed_text(chunk: dict) -> str:
    """
    Compose the string that will be embedded for a single IS chunk.

    Prefixing clause number + title gives the model richer context and
    improves retrieval precision for product-to-standard matching.

    Format::
        IS 10500:2012 § 4.2.1 Bacteriological Quality
        <content>
    """
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


def _embed_texts(
    client: TextEmbedding,
    texts: list[str],
) -> list[list[float]]:
    """
    Embed a list of texts using FastEmbed.

    Handles batching internally.

    Parameters
    ----------
    client : TextEmbedding
        FastEmbed model instance.
    texts : list[str]
        Raw text strings to embed.

    Returns
    -------
    list[list[float]]
        One 384-dimensional float vector per input text.
    """
    all_vectors: list[list[float]] = []
    total = len(texts)

    for start in range(0, total, EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        logger.info(
            "Embedding batch %d–%d of %d texts …",
            start + 1,
            start + len(batch),
            total,
        )
        try:
            embeddings = list(client.embed(batch))
            vectors = [list(emb) for emb in embeddings]
            all_vectors.extend(vectors)
        except Exception as exc:  # noqa: BLE001
            logger.error("Embedding error on batch %d: %s", start, exc)
            # Fill failed batch with zero vectors so indices stay aligned
            all_vectors.extend([[0.0] * 384] * len(batch))

    return all_vectors


def _process_pdf(
    pdf_path: Path,
    gemini_client: TextEmbedding,
    vector_service: VectorService,
    dry_run: bool,
) -> tuple[int, int]:
    """
    Full parse → embed → upsert pipeline for a single PDF.

    Returns
    -------
    (chunks_parsed, chunks_upserted)
    """
    logger.info("━━━ Processing: %s", pdf_path.name)

    # 1. Parse
    try:
        chunks = parse_is_document(pdf_path)
    except Exception as exc:
        logger.error("Failed to parse '%s': %s", pdf_path.name, exc)
        return 0, 0

    if not chunks:
        logger.warning("No chunks extracted from '%s' — skipping.", pdf_path.name)
        return 0, 0

    logger.info("  Parsed %d clause chunks.", len(chunks))

    # 2. Annotate with inferred product category and source file
    standard_code = chunks[0].get("standard_code", "") if chunks else ""
    product_category = _infer_product_category(standard_code)
    for chunk in chunks:
        chunk["product_category"] = product_category
        chunk["source_file"] = pdf_path.name

    # 3. Build embed texts
    embed_texts = [_build_embed_text(c) for c in chunks]

    # 4. Embed
    if dry_run:
        logger.info("  [DRY RUN] Skipping embedding for %d chunks.", len(chunks))
        return len(chunks), 0

    vectors = _embed_texts(gemini_client, embed_texts)

    # Sanity check
    if len(vectors) != len(chunks):
        logger.error(
            "Vector/chunk count mismatch (%d vs %d) for '%s' — skipping upsert.",
            len(vectors), len(chunks), pdf_path.name,
        )
        return len(chunks), 0

    # 5. Upsert
    upserted = vector_service.upsert_chunks(chunks, vectors)
    logger.info(
        "  ✓  Upserted %d vectors  [category: %s]",
        upserted, product_category,
    )
    return len(chunks), upserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest BIS IS-standard PDFs into Qdrant vector database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf-dir",
        default=DEFAULT_PDF_DIR,
        metavar="DIR",
        help=f"Directory containing PDF files (default: {DEFAULT_PDF_DIR})",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + log without writing to Qdrant or calling Gemini.",
    )
    parser.add_argument(
        "--glob",
        default="*.pdf",
        help="Glob pattern for PDF files (default: *.pdf)",
    )
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # 0. Validate environment
    # ------------------------------------------------------------------
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key and not args.dry_run:
        logger.error(
            "GOOGLE_API_KEY environment variable is not set.\n"
            "Export it before running:\n\n"
            "  set GOOGLE_API_KEY=your-key    # Windows\n"
            "  export GOOGLE_API_KEY=your-key # Linux/macOS\n"
        )
        return 1

    # ------------------------------------------------------------------
    # 1. Locate PDFs
    # ------------------------------------------------------------------
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        logger.error("PDF directory not found: %s", pdf_dir.resolve())
        return 1

    pdfs = sorted(pdf_dir.glob(args.glob))
    if not pdfs:
        logger.warning("No PDFs matching '%s' found in: %s", args.glob, pdf_dir.resolve())
        return 0

    logger.info("Found %d PDF(s) in %s", len(pdfs), pdf_dir.resolve())

    # ------------------------------------------------------------------
    # 2. Initialise clients
    # ------------------------------------------------------------------
    gemini_client: TextEmbedding | None = None
    if not args.dry_run:
        gemini_client = TextEmbedding(model_name=EMBEDDING_MODEL)
        logger.info("Gemini client initialised  (model: %s)", EMBEDDING_MODEL)

    vector_svc: VectorService | None = None
    if not args.dry_run:
        vector_svc = VectorService.from_env()
        if args.recreate:
            logger.warning("--recreate flag set: dropping existing collection …")
            vector_svc.recreate_collection()
        info = vector_svc.get_collection_info()
        logger.info(
            "Qdrant collection '%s'  [%d existing points]",
            info["name"], info["points_count"],
        )

    # ------------------------------------------------------------------
    # 3. Process PDFs
    # ------------------------------------------------------------------
    total_parsed   = 0
    total_upserted = 0
    failed: list[str] = []

    t0 = time.perf_counter()
    for pdf_path in pdfs:
        try:
            parsed, upserted = _process_pdf(
                pdf_path,
                gemini_client,   # type: ignore[arg-type]
                vector_svc,      # type: ignore[arg-type]
                dry_run=args.dry_run,
            )
            total_parsed   += parsed
            total_upserted += upserted
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error on '%s': %s", pdf_path.name, exc)
            failed.append(pdf_path.name)

    elapsed = time.perf_counter() - t0

    # ------------------------------------------------------------------
    # 4. Summary
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("Ingestion complete in %.1f s", elapsed)
    logger.info("  PDFs processed : %d", len(pdfs))
    logger.info("  Chunks parsed  : %d", total_parsed)
    logger.info("  Vectors stored : %d", total_upserted)
    if failed:
        logger.warning("  Failed files   : %s", ", ".join(failed))

    if not args.dry_run and vector_svc:
        info = vector_svc.get_collection_info()
        logger.info(
            "  Collection total: %d points", info["points_count"]
        )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
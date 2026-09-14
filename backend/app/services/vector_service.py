"""
app/services/vector_service.py
──────────────────────────────
Qdrant vector database service for BIS IS-standard semantic retrieval.

Design decisions
----------------
* Collection name  : "bis_standards_v3"
* Distance metric  : COSINE  (best for semantic similarity on unit-norm embeddings)
* Vector size      : 384     (Using FastEmbed default model BAAI/bge-small-en-v1.5)
* Payload indices  : standard_code, clause_number, product_category
  so Qdrant can filter at query time without scanning all vectors.
* Local mode       : runs an in-process Qdrant instance (no Docker needed);
  switch to QdrantClient(url=...) for a deployed cluster.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_NAME: str = "bis_standards_v3"
VECTOR_SIZE: int = 384          # fastembed default dimensionality
DISTANCE: Distance = Distance.COSINE

# Payload field names – kept as constants so callers never have to hard-code them
F_STANDARD_CODE: str = "standard_code"
F_CLAUSE_NUMBER: str = "clause_number"
F_CLAUSE_TITLE: str = "clause_title"
F_PRODUCT_CATEGORY: str = "product_category"
F_TEXT: str = "text"
F_PAGE_NUMBER: str = "page_number"
F_SOURCE_FILE: str = "source_file"


# ---------------------------------------------------------------------------
# VectorService
# ---------------------------------------------------------------------------

class VectorService:
    """
    Thin wrapper around QdrantClient that owns collection lifecycle,
    upsertion, and semantic search for BIS IS-standard chunks.

    Parameters
    ----------
    storage_path:
        Directory where Qdrant persists data to disk.
        Defaults to ``data/qdrant_storage`` relative to the project root.
        Set to ``":memory:"`` for an ephemeral, test-only instance.
    host / port:
        When set, connects to a remote / Docker Qdrant instead of local mode.
    """

    def __init__(
        self,
        storage_path: str | Path | None = None,
        host: str | None = None,
        port: int = 6333,
    ) -> None:
        if host:
            # Remote Qdrant (Docker / cloud)
            self._client = QdrantClient(host=host, port=port)
            logger.info("Connected to remote Qdrant at %s:%d", host, port)
        else:
            # Local in-process Qdrant (no Docker required)
            path = Path(storage_path or "data/qdrant_storage")
            path.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(path))
            logger.info("Qdrant local storage at: %s", path.resolve())

        self._ensure_collection()

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        if COLLECTION_NAME in existing:
            logger.info("Collection '%s' already exists.", COLLECTION_NAME)
            return

        self._client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=DISTANCE,
                # Store vectors on disk to keep RAM usage low for large corpora
                on_disk=True,
            ),
        )

        # Create payload indices for fast filtered retrieval
        self._create_payload_indices()
        logger.info("Collection '%s' created with COSINE index.", COLLECTION_NAME)

    def _create_payload_indices(self) -> None:
        """
        Create keyword indices on high-selectivity payload fields so Qdrant
        can evaluate filters before the ANN search (pre-filtering).
        """
        keyword_fields = [
            F_STANDARD_CODE,
            F_CLAUSE_NUMBER,
            F_PRODUCT_CATEGORY,
        ]
        for field in keyword_fields:
            self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.debug("Payload index created on '%s'.", field)

    def recreate_collection(self) -> None:
        """
        Drop and recreate the collection — useful during full re-ingestion.

        .. warning::
            This deletes ALL stored vectors. Use with care.
        """
        self._client.delete_collection(COLLECTION_NAME)
        logger.warning("Collection '%s' deleted.", COLLECTION_NAME)
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        """
        Upsert a batch of IS-standard chunks with their pre-computed embeddings.

        Parameters
        ----------
        chunks:
            List of ISChunk dicts produced by ``pdf_parser.parse_is_document``.
            Each dict must have keys: standard_code, clause_number,
            clause_title, content, page_number.
            Optional extra keys (e.g. product_category, source_file) are
            forwarded to Qdrant payload as-is.
        embeddings:
            Corresponding embedding vectors (one per chunk).

        Returns
        -------
        int
            Number of points upserted.

        Raises
        ------
        ValueError
            If len(chunks) != len(embeddings).
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings."
            )

        points: list[PointStruct] = []
        for chunk, vector in zip(chunks, embeddings):
            payload = {
                F_STANDARD_CODE:    chunk.get("standard_code", ""),
                F_CLAUSE_NUMBER:    chunk.get("clause_number", ""),
                F_CLAUSE_TITLE:     chunk.get("clause_title", ""),
                F_PRODUCT_CATEGORY: chunk.get("product_category", ""),
                F_TEXT:             chunk.get("content", ""),
                F_PAGE_NUMBER:      chunk.get("page_number", 0),
                F_SOURCE_FILE:      chunk.get("source_file", ""),
            }
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )

        # Qdrant recommends batch sizes of 100–512 for best throughput
        BATCH = 256
        for i in range(0, len(points), BATCH):
            batch = points[i : i + BATCH]
            self._client.upsert(collection_name=COLLECTION_NAME, points=batch)
            logger.debug("Upserted batch %d–%d.", i, i + len(batch) - 1)
            
        # --- Relational Database Insertion ---
        try:
            from app.database.session import SessionLocal
            from app.models.db_models import Product, Standard, ProductStandard, KnowledgeChunk
            
            db = SessionLocal()
            
            # Cache to prevent repetitive DB queries per batch
            standard_cache = {}
            
            for point in points:
                payload = point.payload
                is_number = payload.get(F_STANDARD_CODE)
                source_file = payload.get(F_SOURCE_FILE, 'unknown.pdf')
                
                if not is_number or is_number == 'N/A':
                    is_number = source_file.replace('.pdf', '').replace('_', ' ')
                    
                if is_number not in standard_cache:
                    standard = db.query(Standard).filter_by(is_number=is_number).first()
                    if not standard:
                        standard = Standard(is_number=is_number, title=source_file)
                        db.add(standard)
                        db.commit()
                        db.refresh(standard)
                        
                    # Insert Product based on inferred product category
                    prod_cat_name = payload.get(F_PRODUCT_CATEGORY, "General Product")
                    if not prod_cat_name or prod_cat_name == "Unknown":
                        prod_cat_name = "General Product"
                        
                    product_record = db.query(Product).filter_by(product_name=prod_cat_name).first()
                    if not product_record:
                        product_record = Product(product_name=prod_cat_name)
                        db.add(product_record)
                        db.commit()
                        db.refresh(product_record)
                        
                    # Create relationship if not exists
                    existing_ps = db.query(ProductStandard).filter_by(
                        product_id=product_record.product_id,
                        standard_id=standard.standard_id
                    ).first()
                    
                    if not existing_ps:
                        ps = ProductStandard(
                            product_id=product_record.product_id,
                            standard_id=standard.standard_id,
                            relationship_type="Product Standard"
                        )
                        db.add(ps)
                        db.commit()
                        
                    standard_cache[is_number] = standard
                    
                standard = standard_cache[is_number]
                
                # Insert Chunk
                chunk_id = point.id
                existing_chunk = db.query(KnowledgeChunk).filter_by(chunk_id=chunk_id).first()
                if not existing_chunk:
                    chunk = KnowledgeChunk(
                        chunk_id=chunk_id,
                        standard_id=standard.standard_id,
                        clause_number=payload.get(F_CLAUSE_NUMBER),
                        page_number=payload.get(F_PAGE_NUMBER),
                        text=payload.get(F_TEXT, '')
                    )
                    db.add(chunk)
            
            db.commit()
            db.close()
        except Exception as db_exc:
            logger.error(f"Failed to sync chunks to Relational DB: {db_exc}")

        logger.info("Upserted %d points into '%s'.", len(points), COLLECTION_NAME)
        return len(points)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        standard_code: str | None = None,
        product_category: str | None = None,
        score_threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """
        Semantic nearest-neighbour search over the BIS standards corpus.

        Parameters
        ----------
        query_vector:
            Embedding of the search query (768-dim for text-embedding-004).
        top_k:
            Number of results to return.
        standard_code:
            Optional exact-match filter (e.g. "IS 10500:2012").
        product_category:
            Optional category filter (e.g. "Drinking Water").
        score_threshold:
            Minimum cosine similarity; results below this are discarded.

        Returns
        -------
        list[dict]
            Each result dict contains all payload fields plus ``score``.
        """
        must_conditions = []
        if standard_code:
            must_conditions.append(
                FieldCondition(
                    key=F_STANDARD_CODE,
                    match=MatchValue(value=standard_code),
                )
            )
        if product_category:
            must_conditions.append(
                FieldCondition(
                    key=F_PRODUCT_CATEGORY,
                    match=MatchValue(value=product_category),
                )
            )

        query_filter = Filter(must=must_conditions) if must_conditions else None

        response = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        hits = response.points

        return [
            {
                "score":            hit.score,
                "standard_code":    hit.payload.get(F_STANDARD_CODE, ""),
                "clause_number":    hit.payload.get(F_CLAUSE_NUMBER, ""),
                "clause_title":     hit.payload.get(F_CLAUSE_TITLE, ""),
                "product_category": hit.payload.get(F_PRODUCT_CATEGORY, ""),
                "text":             hit.payload.get(F_TEXT, ""),
                "page_number":      hit.payload.get(F_PAGE_NUMBER, 0),
                "source_file":      hit.payload.get(F_SOURCE_FILE, ""),
            }
            for hit in hits
        ]

    def get_collection_info(self) -> dict[str, Any]:
        """Return a summary dict of the collection (point count, status, etc.)."""
        info = self._client.get_collection(COLLECTION_NAME)
        return {
            "name":          COLLECTION_NAME,
            "vector_size":   VECTOR_SIZE,
            "distance":      DISTANCE.value,
            "points_count":  info.points_count,
            "status":        info.status.value if info.status else "unknown",
            "indexed_vectors_count": info.indexed_vectors_count,
        }

    # ------------------------------------------------------------------
    # Dependency-injection helper for FastAPI
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "VectorService":
        """
        Construct a VectorService from environment variables.

        Environment variables
        ---------------------
        QDRANT_HOST   : hostname of a remote Qdrant (omit for local mode)
        QDRANT_PORT   : port of remote Qdrant (default 6333)
        QDRANT_PATH   : local storage path (default "data/qdrant_storage")
        """
        host = os.getenv("QDRANT_HOST")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        path = os.getenv("QDRANT_PATH", "data/qdrant_storage")
        return cls(storage_path=None if host else path, host=host, port=port)

_vector_service_instance: VectorService | None = None

def get_vector_service() -> VectorService:
    """
    Get or create a singleton instance of VectorService for the current process.
    This prevents multiple local Qdrant clients from locking the database
    in the same process.
    """
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorService.from_env()
    return _vector_service_instance
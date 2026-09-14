"""
app/services/__init__.py
─────────────────────────
Shared service singletons.

Qdrant local mode only allows ONE client to hold the storage lock.
We therefore create a single VectorService instance here and share it
across RAGService, QueryRouter, and the ingest/status endpoints.
"""

from __future__ import annotations

import logging
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

# ── Shared VectorService singleton ────────────────────────────────────────────
_vector_service: VectorService | None = None


def get_shared_vector_service() -> VectorService:
    """
    Return the process-wide VectorService singleton.

    The first call creates the instance (from env vars); subsequent calls
    return the same object.  This avoids the Qdrant local-mode lock conflict
    that occurs when multiple QdrantClient instances try to open the same
    storage directory concurrently.
    """
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService.from_env()
        logger.info("Shared VectorService singleton created.")
    return _vector_service

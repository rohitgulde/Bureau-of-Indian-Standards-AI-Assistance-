"""
main.py
────────
BIS Knowledge Portal — FastAPI application entrypoint.

Startup sequence
----------------
1. Load .env (python-dotenv) so GOOGLE_API_KEY etc. are available.
2. Initialise SQLite DB via init_db() (creates tables if absent).
3. Register all API routers.
4. Serve via uvicorn (run: uvicorn main:app --reload).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Load .env before any service imports that read env vars ──────────────────
load_dotenv(Path(__file__).parent / ".env", override=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bis.main")

# ── DB + Routers (imported after dotenv so env vars are set) ─────────────────
from app.database.session import init_db               # noqa: E402
from app.routers import rag as rag_router              # noqa: E402
from app.routers import chat as chat_router            # noqa: E402
from app.routers import sarvam as sarvam_router        # noqa: E402
from app.routers import ingest as ingest_router        # noqa: E402
from app.api import endpoints as api_endpoints         # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup : create DB tables.
    Shutdown: (add cleanup here if needed e.g. close DB pools).
    """
    logger.info("Starting BIS Knowledge Portal API …")
    init_db()
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BIS Knowledge Portal API",
    version="1.0.0",
    description=(
        "AI-powered API for BIS IS-standard retrieval (RAG), "
        "Lab Finder, Certification Scheme lookup, and Consumer FAQ."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    # Next.js default ports (3000 = primary, 3001 = fallback)
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:3001,http://127.0.0.1:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# Internal service routers (RAG, classifier, Sarvam):
app.include_router(rag_router.router)
app.include_router(chat_router.router)
app.include_router(sarvam_router.router)
app.include_router(ingest_router.router)

# Frontend-facing unified API (POST /api/chat, /api/voice-chat, GET /api/labs, /api/schemes):
app.include_router(api_endpoints.router)


# ─────────────────────────────────────────────────────────────────────────────
# Root endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "BIS Knowledge Portal API",
        "version": "1.0.0",
        "docs":    "/docs",
        "status":  "running",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}

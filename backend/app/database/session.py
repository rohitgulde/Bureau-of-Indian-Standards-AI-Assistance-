"""
app/database/session.py
────────────────────────
SQLAlchemy engine, session factory, and Base declarative class.

All other modules import from here:

    from app.database.session import Base, get_db, engine

Usage (FastAPI dependency injection)
-------------------------------------
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.database.session import get_db

    @app.get("/labs")
    def list_labs(db: Session = Depends(get_db)):
        ...

Usage (scripts / seed)
-----------------------
    from app.database.session import SessionLocal, engine, Base
    Base.metadata.create_all(bind=engine)  # create tables
    db = SessionLocal()
    ...
    db.close()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

# Resolve the DB path relative to the backend root, but allow override via env.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = _BACKEND_ROOT / "app" / "database" / "bis_master.db"

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH}",
)

logger.info("Database URL: %s", DATABASE_URL)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# connect_args is SQLite-specific — enables WAL mode for concurrent access.
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    # Echo SQL only when DEBUG env var is set to avoid noisy prod logs
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)


# Enable WAL mode and foreign keys for SQLite on every new connection
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # avoid lazy-load issues after commit
)


# ---------------------------------------------------------------------------
# Declarative Base — all models inherit from this
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """
    Yield a SQLAlchemy session, always closing it when the request ends.

    Usage::

        @router.get("/labs")
        def list_labs(db: Session = Depends(get_db)):
            return db.query(Laboratory).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Convenience: create all tables (called from main.py startup)
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables defined in ORM models if they do not already exist."""
    # Import models so their metadata is registered on Base before create_all
    import app.models.db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised.")
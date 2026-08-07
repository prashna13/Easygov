"""
database.py
-----------
SQLAlchemy engine and session factory for EasyGov Nepal.

Database location: db_storage/easygov.db (SQLite)

To upgrade to PostgreSQL later, replace DATABASE_URL with:
    DATABASE_URL = "postgresql://user:password@host/dbname"
and run: pip install psycopg2-binary
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ── DATABASE URL ──────────────────────────────────────────────────────────────
# SQLite path is relative to where the FastAPI server is launched from (project root).
# Using /// for a relative path, //// for absolute.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db_storage/easygov.db")

# ── ENGINE ────────────────────────────────────────────────────────────────────
# check_same_thread=False is required for SQLite to work with FastAPI's
# async request handling (multiple threads may share one connection).
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,  # Set True to print all SQL statements to console (useful for debugging)
)

# ── SESSION FACTORY ───────────────────────────────────────────────────────────
# autocommit=False: changes must be explicitly committed (safer default)
# autoflush=False:  prevents implicit writes before a query (avoids surprises)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── DECLARATIVE BASE ──────────────────────────────────────────────────────────
# All ORM model classes in models.py will inherit from this Base.
Base = declarative_base()


# ── DEPENDENCY (for FastAPI endpoints) ───────────────────────────────────────
def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Guarantees the session is closed after the request completes,
    even if an exception is raised.

    Usage in a route:
        from app.database import get_db
        from sqlalchemy.orm import Session

        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Database engine, session management, and configuration for ClearPay AI.

Supports SQLite by default (at C:\\ClearPayAI\\backend\\clearpayai.db) and
PostgreSQL via DATABASE_URL environment variable (supports Neon, Render, Supabase).
"""

import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables
_BACKEND_DIR = Path(__file__).parent.resolve()
load_dotenv(_BACKEND_DIR / ".env")

# Default database file in backend directory: C:\ClearPayAI\backend\clearpayai.db
DEFAULT_DB_FILE = _BACKEND_DIR / "clearpayai.db"


def resolve_database_url(url: str | None = None) -> str:
    """Resolve database URL ensuring SQLite relative paths are anchored to backend dir,
    and PostgreSQL URLs with legacy 'postgres://' scheme are converted to 'postgresql://'."""
    raw_url = url or os.getenv("DATABASE_URL")
    if not raw_url:
        return f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

    # Handle PostgreSQL legacy scheme (common in Render / Neon / Supabase)
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # Handle sqlite relative formats: sqlite:///./clearpayai.db or sqlite:///clearpayai.db
    if raw_url.startswith("sqlite:///./"):
        filename = raw_url.removeprefix("sqlite:///./")
        return f"sqlite:///{(_BACKEND_DIR / filename).resolve().as_posix()}"

    # In-memory sqlite URL for testing
    if raw_url == "sqlite:///:memory:":
        return raw_url

    # Relative filename like sqlite:///test.db
    if raw_url.startswith("sqlite:///") and not raw_url.startswith("sqlite:////") and ":" not in raw_url[10:]:
        filename = raw_url.removeprefix("sqlite:///")
        return f"sqlite:///{(_BACKEND_DIR / filename).resolve().as_posix()}"

    return raw_url


DATABASE_URL = resolve_database_url()

is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "pool_pre_ping": True,
}

if is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL cloud settings (Render / Neon serverless)
    _engine_kwargs["pool_recycle"] = 300
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(
    DATABASE_URL,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy session and closing it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Initialize database tables idempotently without deleting existing records."""
    # Import models here so they register with Base.metadata before create_all
    import models  # noqa: F401
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

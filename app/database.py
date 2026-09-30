"""Database engine and session management (SQLAlchemy 2.0 style)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# Make sure the directory for a file-based SQLite database exists.
if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    if db_path and db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (import models first so they are registered)."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

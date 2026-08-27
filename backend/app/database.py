"""SQLAlchemy setup. Works with SQLite out of the box; point ``DATABASE_URL``
at ``postgresql://user:pass@host/db`` to use PostgreSQL."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite"):
        path = url.split("///")[-1]
        if path and path != ":memory:":
            dirname = os.path.dirname(path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)


class Base(DeclarativeBase):
    pass


_ensure_sqlite_dir(settings.database_url)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    # Import models so they register on Base.metadata
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

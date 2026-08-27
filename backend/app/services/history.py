"""Study-history queries (thin wrapper kept separate for clarity)."""

from sqlalchemy.orm import Session

from .. import models
from . import analytics


def history(db: Session, user: models.User, limit: int = 50) -> list[dict]:
    return analytics.history(db, user, limit=limit)

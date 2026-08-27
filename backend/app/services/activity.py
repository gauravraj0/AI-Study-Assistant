from sqlalchemy.orm import Session

from .. import models


def log_activity(db: Session, user: models.User, type_: str, document_id: int | None, detail: str) -> None:
    db.add(models.Activity(user_id=user.id, type=type_, document_id=document_id, detail=detail[:500]))

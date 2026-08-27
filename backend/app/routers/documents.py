from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..services import documents as doc_service
from ..services import auth as auth_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _doc_out(d: models.Document) -> schemas.DocumentOut:
    out = schemas.DocumentOut.model_validate(d)
    out.quiz_count = len(d.quizzes)
    out.flashcard_count = len(d.flashcard_sets)
    return out


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    docs = (
        db.query(models.Document)
        .options(selectinload(models.Document.quizzes), selectinload(models.Document.flashcard_sets))
        .filter(models.Document.user_id == user.id)
        .order_by(models.Document.created_at.desc())
        .all()
    )
    return [_doc_out(d) for d in docs]


@router.post("", response_model=schemas.DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    content = file.file.read()
    doc = doc_service.ingest_document(db, user, file, content)
    return _doc_out(doc)


@router.get("/{doc_id}", response_model=schemas.DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    d = db.get(models.Document, doc_id)
    if d is None or d.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _doc_out(d)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    d = db.get(models.Document, doc_id)
    if d is None or d.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc_service.delete_document(db, user, d)
    return None


@router.post("/{doc_id}/summarize", response_model=schemas.DocumentOut)
def summarize_document(
    doc_id: int,
    body: schemas.ReSummarizeRequest | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    d = db.get(models.Document, doc_id)
    if d is None or d.user_id != user.id or d.status != "ready":
        raise HTTPException(status_code=404, detail="Document not found or not ready.")
    max_words = body.max_words if body else 180
    doc_service.resummarize(db, user, d, max_words=max_words)
    return _doc_out(d)

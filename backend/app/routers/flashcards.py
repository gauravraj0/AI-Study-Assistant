from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..services import auth as auth_service
from ..services import flashcards as fc_service

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


def _set_out(s: models.FlashcardSet) -> schemas.FlashcardSetOut:
    out = schemas.FlashcardSetOut.model_validate(s)
    out.document_name = s.document.original_name if s.document else None
    out.card_count = len(s.cards)
    out.reviewed_count = sum(1 for c in s.cards if c.times_seen > 0)
    return out


@router.get("/sets", response_model=list[schemas.FlashcardSetOut])
def list_sets(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    sets = (
        db.query(models.FlashcardSet)
        .options(selectinload(models.FlashcardSet.cards), selectinload(models.FlashcardSet.document))
        .filter(models.FlashcardSet.user_id == user.id)
        .order_by(models.FlashcardSet.created_at.desc())
        .all()
    )
    return [_set_out(s) for s in sets]


@router.post("/generate", response_model=schemas.FlashcardSetOut, status_code=201)
def generate_set(
    body: schemas.FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        s = fc_service.generate(db, user, body.document_id, body.difficulty, body.count)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _set_out(s)


@router.get("/sets/{set_id}", response_model=list[schemas.FlashcardOut])
def get_cards(
    set_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        s = fc_service.get_set(db, user, set_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return s.cards


@router.post("/cards/{card_id}/review")
def review_card(
    card_id: int,
    body: schemas.FlashcardReviewRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    card = db.get(models.Flashcard, card_id)
    if card is None or card.set.user_id != user.id:
        raise HTTPException(status_code=404, detail="Flashcard not found.")
    fc_service.review(db, user, card, body.quality)
    return {"ok": True, "interval_days": card.interval_days, "ease": card.ease, "times_seen": card.times_seen}

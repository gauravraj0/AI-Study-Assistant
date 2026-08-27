"""Flashcard set generation + lightweight spaced-repetition review."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from ..llm import get_provider
from ..rag import all_contexts
from .activity import log_activity


def generate(
    db: Session, user: models.User, document_id: int, difficulty: str, count: int
) -> models.FlashcardSet:
    doc = db.get(models.Document, document_id)
    if doc is None or doc.user_id != user.id or doc.status != "ready":
        raise LookupError("Document not found or not ready.")
    contexts = all_contexts([doc.id], limit=80)
    cards = get_provider().generate_flashcards(contexts, count=count, difficulty=difficulty)
    if not cards:
        raise LookupError("Could not extract enough material to build flashcards from this document.")

    s = models.FlashcardSet(
        user_id=user.id,
        document_id=doc.id,
        difficulty=difficulty,
        title=f"{difficulty.capitalize()} flashcards — {doc.original_name}",
    )
    db.add(s)
    db.flush()
    for i, c in enumerate(cards):
        db.add(models.Flashcard(set_id=s.id, idx=i, front=c.front, back=c.back))
    log_activity(db, user, "flashcards_generated", doc.id, f"Generated {len(cards)} {difficulty} flashcards")
    db.commit()
    db.refresh(s)
    return s


def get_set(db: Session, user: models.User, set_id: int) -> models.FlashcardSet:
    s = db.get(models.FlashcardSet, set_id)
    if s is None or s.user_id != user.id:
        raise LookupError("Flashcard set not found.")
    return s


def review(db: Session, user: models.User, card: models.Flashcard, quality: int) -> models.Flashcard:
    """SM-2 inspired update: 0=again, 1=good, 2=easy."""
    card.times_seen += 1
    card.last_reviewed = datetime.now(timezone.utc)
    if quality == 0:
        card.interval_days = 0.0
        card.ease = max(1.3, card.ease - 0.2)
    elif quality == 1:
        card.interval_days = max(1.0, card.interval_days * card.ease)
        card.ease = max(1.3, card.ease + 0.05)
    else:
        card.interval_days = max(1.0, card.interval_days * (card.ease + 0.3))
        card.ease = min(3.0, card.ease + 0.15)
    db.commit()
    db.refresh(card)
    return card

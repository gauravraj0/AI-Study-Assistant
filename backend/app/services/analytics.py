"""Performance analytics, progress tracking, study history."""

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def overview(db: Session, user: models.User) -> dict:
    docs = db.query(models.Document).filter(models.Document.user_id == user.id).all()
    all_quizzes = db.query(models.Quiz).filter(models.Quiz.user_id == user.id).all()
    quizzes = [q for q in all_quizzes if q.submitted_at is not None]
    sets = db.query(models.FlashcardSet).filter(models.FlashcardSet.user_id == user.id).all()
    cards = [c for s in sets for c in s.cards]
    msgs = (
        db.query(func.count(models.ChatMessage.id))
        .join(models.ChatSession, models.ChatMessage.session_id == models.ChatSession.id)
        .filter(models.ChatSession.user_id == user.id)
        .scalar()
        or 0
    )

    scores = [q.score for q in quizzes if q.score is not None]
    passed = sum(1 for q in quizzes if q.passed)

    # streak: consecutive days (ending today or yesterday) with any activity
    from datetime import timedelta

    day_rows = (
        db.query(func.date(models.Activity.created_at))
        .filter(models.Activity.user_id == user.id)
        .all()
    )
    days = {str(r[0]) for r in day_rows if r[0]}
    streak = 0
    if days:
        today = datetime.now(timezone.utc).date()
        start = today if str(today) in days else today - timedelta(days=1)
        for i in range(365):
            if str(start - timedelta(days=i)) in days:
                streak += 1
            else:
                break

    recent = (
        db.query(models.Activity)
        .filter(models.Activity.user_id == user.id)
        .order_by(models.Activity.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "documents": len(docs),
        "ready_documents": sum(1 for d in docs if d.status == "ready"),
        "quizzes": len(all_quizzes),
        "submitted_quizzes": len(quizzes),
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "pass_rate": round(100 * passed / len(quizzes), 1) if quizzes else None,
        "flashcards_reviewed": sum(c.times_seen for c in cards),
        "flashcards_total": len(cards),
        "chat_messages": msgs,
        "streak_days": streak,
        "recent_activity": [
            {"type": a.type, "detail": a.detail, "document_id": a.document_id, "created_at": a.created_at}
            for a in recent
        ],
    }


def score_history(db: Session, user: models.User) -> list[dict]:
    rows = (
        db.query(models.Quiz)
        .filter(models.Quiz.user_id == user.id, models.Quiz.submitted_at.isnot(None))
        .order_by(models.Quiz.submitted_at.asc())
        .all()
    )
    return [
        {
            "date": q.submitted_at.strftime("%b %d %H:%M"),
            "score": q.score or 0,
            "title": q.title,
            "difficulty": q.difficulty,
        }
        for q in rows
    ]


def topic_accuracy(db: Session, user: models.User) -> list[dict]:
    """Per-topic accuracy, using the per-question result recorded at submit time."""
    rows = (
        db.query(models.QuizQuestion)
        .join(models.Quiz, models.QuizQuestion.quiz_id == models.Quiz.id)
        .filter(models.Quiz.user_id == user.id, models.Quiz.submitted_at.isnot(None))
        .all()
    )
    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for qq in rows:
        total = agg[qq.topic][1] + 1
        correct = agg[qq.topic][0] + (1 if qq.was_correct else 0)
        agg[qq.topic] = [correct, total]
    out = []
    for topic, (correct, total) in sorted(agg.items(), key=lambda kv: kv[1][1], reverse=True):
        out.append({"topic": topic, "answered": total, "correct": correct, "accuracy": round(100 * correct / total, 1)})
    return out[:12]


def progress(db: Session, user: models.User) -> list[dict]:
    docs = db.query(models.Document).filter(models.Document.user_id == user.id).order_by(models.Document.created_at.desc()).all()
    out = []
    for d in docs:
        quizzes = [q for q in d.quizzes if q.submitted_at is not None]
        best = max((q.score for q in quizzes if q.score is not None), default=None)
        sets = d.flashcard_sets
        cards_total = sum(len(s.cards) for s in sets)
        cards_reviewed = sum(c.times_seen for s in sets for c in s.cards)
        acts = (
            db.query(models.Activity)
            .filter(models.Activity.user_id == user.id, models.Activity.document_id == d.id)
            .order_by(models.Activity.created_at.desc())
            .first()
        )
        chat_messages = (
            db.query(func.count(models.ChatMessage.id))
            .join(models.ChatSession, models.ChatMessage.session_id == models.ChatSession.id)
            .filter(models.ChatSession.user_id == user.id, models.ChatSession.document_id == d.id)
            .scalar()
            or 0
        )
        pct = 0.0
        if d.status == "ready":
            pct = 25.0  # material processed & summarized
            if quizzes:
                pct += 30.0 + min(20.0, (best or 0) / 5)
            if cards_total:
                pct += 10.0 * min(1.0, cards_reviewed / max(1, cards_total))
            if acts:
                pct += 15.0
        out.append(
            {
                "document_id": d.id,
                "document_name": d.original_name,
                "status": d.status,
                "progress_pct": round(min(100.0, pct), 0),
                "quizzes": len(quizzes),
                "best_score": best,
                "flashcards_total": cards_total,
                "flashcards_reviewed": cards_reviewed,
                "chat_messages": chat_messages,
                "last_activity": acts.created_at if acts else None,
            }
        )
    return out


def history(db: Session, user: models.User, limit: int = 50) -> list[dict]:
    rows = (
        db.query(models.Activity).filter(models.Activity.user_id == user.id)
        .order_by(models.Activity.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": a.id, "type": a.type, "detail": a.detail, "document_id": a.document_id, "created_at": a.created_at}
        for a in rows
    ]

"""Personalised study-plan generation."""

from sqlalchemy.orm import Session

from .. import models
from ..llm import get_provider
from .activity import log_activity


def _user_profile(db: Session, user: models.User) -> dict:
    docs = (
        db.query(models.Document).filter(models.Document.user_id == user.id, models.Document.status == "ready").all()
    )
    from ..llm.local import key_terms
    from ..rag import get_vector_store

    store = get_vector_store()
    doc_infos = []
    for d in docs:
        chunks = store.all_chunks(d.id, limit=60)
        text = " ".join(c["text"] for c in chunks)
        doc_infos.append({"title": d.original_name, "topics": key_terms(text, 5), "chunks": len(chunks)})

    quizzes = (
        db.query(models.Quiz)
        .filter(models.Quiz.user_id == user.id, models.Quiz.submitted_at.isnot(None))
        .order_by(models.Quiz.submitted_at.desc())
        .limit(10)
        .all()
    )
    return {
        "documents": doc_infos,
        "recent_scores": [q.score for q in quizzes if q.score is not None],
    }


def generate(db: Session, user: models.User) -> models.StudyPlan:
    profile = _user_profile(db, user)
    if not profile["documents"]:
        raise LookupError("Upload at least one document first — the plan is built from your material.")
    plan_data = get_provider().generate_study_plan(profile)
    plan = models.StudyPlan(
        user_id=user.id,
        title=str(plan_data.get("title", "Personalised study plan"))[:255],
        goal=str(plan_data.get("goal", "")),
        total_days=int(plan_data.get("total_days", 5)),
        days=plan_data.get("days", []),
    )
    db.add(plan)
    log_activity(db, user, "study_plan_generated", None, f"Generated “{plan.title}”")
    db.commit()
    db.refresh(plan)
    return plan

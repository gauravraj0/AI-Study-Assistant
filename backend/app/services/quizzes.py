"""Quiz generation (MCQ) + submission/scoring."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from ..llm import get_provider
from ..rag import all_contexts
from .activity import log_activity


def _check_doc(db: Session, user: models.User, document_id: int) -> models.Document:
    doc = db.get(models.Document, document_id)
    if doc is None or doc.user_id != user.id:
        raise LookupError("Document not found.")
    if doc.status != "ready":
        raise LookupError(f"Document is not ready (status: {doc.status}).")
    return doc


def generate(
    db: Session, user: models.User, document_id: int, difficulty: str, count: int
) -> models.Quiz:
    doc = _check_doc(db, user, document_id)
    contexts = all_contexts([doc.id], limit=80)
    if len(contexts) < 3:
        raise LookupError("Document has too little content to build a quiz from.")

    mcqs = get_provider().generate_mcqs(contexts, count=count, difficulty=difficulty)
    if len(mcqs) < 3:
        raise LookupError("Not enough distinct facts in this document to generate a fair quiz.")

    quiz = models.Quiz(
        user_id=user.id,
        document_id=doc.id,
        difficulty=difficulty,
        title=f"{difficulty.capitalize()} quiz — {doc.original_name}",
        num_questions=len(mcqs),
    )
    db.add(quiz)
    db.flush()
    for i, m in enumerate(mcqs):
        db.add(
            models.QuizQuestion(
                quiz_id=quiz.id,
                idx=i,
                topic=m.topic or "general",
                question=m.question,
                options=m.options,
                correct_index=m.correct_index,
                explanation=m.explanation,
                difficulty=m.difficulty or difficulty,
            )
        )
    log_activity(db, user, "quiz_generated", doc.id, f"Generated {len(mcqs)} {difficulty} questions for “{doc.original_name}”")
    db.commit()
    db.refresh(quiz)
    return quiz


def get_quiz(db: Session, user: models.User, quiz_id: int, include_answers: bool = False) -> models.Quiz:
    q = db.get(models.Quiz, quiz_id)
    if q is None or q.user_id != user.id:
        raise LookupError("Quiz not found.")
    return q


def submit(db: Session, user: models.User, quiz: models.Quiz, answers: list[int]) -> dict:
    if quiz.submitted_at is not None:
        raise LookupError("Quiz already submitted.")
    qs = quiz.questions
    if len(answers) != len(qs):
        raise LookupError("Answer count does not match question count.")

    correct = 0
    results = []
    for i, q in enumerate(qs):
        given = answers[i]
        ok = given == q.correct_index
        q.was_correct = ok
        correct += int(ok)
        results.append(
            {
                "question_id": q.id,
                "your_answer": given,
                "correct_index": q.correct_index,
                "correct": ok,
                "question": q.question,
                "topic": q.topic,
                "options": q.options,
                "explanation": q.explanation,
            }
        )

    score = round(100 * correct / len(qs))
    quiz.score = score
    quiz.passed = score >= 60
    quiz.submitted_at = datetime.now(timezone.utc)
    log_activity(db, user, "quiz_completed", quiz.document_id, f"Scored {score}% on “{quiz.title}” ({correct}/{len(qs)})")
    db.commit()
    return {"quiz": quiz, "results": results, "correct": correct, "total": len(qs), "score": score}

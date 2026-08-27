from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..services import auth as auth_service
from ..services import quizzes as quiz_service

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


def _quiz_out(q: models.Quiz) -> schemas.QuizOut:
    out = schemas.QuizOut.model_validate(q)
    out.document_name = q.document.original_name if q.document else None
    return out


def _question_out(qq: models.QuizQuestion, include_answers: bool = False, your_answer: int | None = None) -> schemas.QuizQuestionOut:
    out = schemas.QuizQuestionOut.model_validate(qq)
    out.correct_index = qq.correct_index if include_answers else None
    if your_answer is not None:
        out.your_answer = your_answer
    return out


@router.get("", response_model=list[schemas.QuizOut])
def list_quizzes(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    qs = (
        db.query(models.Quiz)
        .options(selectinload(models.Quiz.document))
        .filter(models.Quiz.user_id == user.id)
        .order_by(models.Quiz.created_at.desc())
        .all()
    )
    return [_quiz_out(q) for q in qs]


@router.post("/generate", response_model=schemas.QuizOut, status_code=201)
def generate_quiz(
    body: schemas.QuizGenerateRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        q = quiz_service.generate(db, user, body.document_id, body.difficulty, body.count)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _quiz_out(q)


@router.get("/{quiz_id}", response_model=schemas.QuizDetail)
def get_quiz(
    quiz_id: int,
    include_answers: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        q = quiz_service.get_quiz(db, user, quiz_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    questions = [
        _question_out(qq, include_answers=include_answers or q.submitted_at is not None)
        for qq in q.questions
    ]
    return schemas.QuizDetail(quiz=_quiz_out(q), questions=questions)


@router.post("/{quiz_id}/submit", response_model=schemas.QuizDetail)
def submit_quiz(
    quiz_id: int,
    body: schemas.QuizSubmitRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        q = quiz_service.get_quiz(db, user, quiz_id)
        data = quiz_service.submit(db, user, q, body.answers)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    q = data["quiz"]
    results = data["results"]
    questions = []
    for r in results:
        qq = next(x for x in q.questions if x.id == r["question_id"])
        questions.append(
            _question_out(
                qq,
                include_answers=True,
                your_answer=r["your_answer"],
            )
        )
    return schemas.QuizDetail(quiz=_quiz_out(q), questions=questions, results=results)

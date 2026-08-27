from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import auth as auth_service
from ..services import plans as plan_service

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[schemas.StudyPlanOut])
def list_plans(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return (
        db.query(models.StudyPlan)
        .filter(models.StudyPlan.user_id == user.id)
        .order_by(models.StudyPlan.created_at.desc())
        .all()
    )


@router.post("/generate", response_model=schemas.StudyPlanOut, status_code=201)
def generate_plan(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        return plan_service.generate(db, user)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e))

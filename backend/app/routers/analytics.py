from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import analytics, auth as auth_service, history as history_service

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/overview", response_model=schemas.OverviewStats)
def overview(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return analytics.overview(db, user)


@router.get("/analytics/scores", response_model=list[schemas.ScorePoint])
def scores(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return analytics.score_history(db, user)


@router.get("/analytics/topics", response_model=list[schemas.TopicAccuracy])
def topics(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return analytics.topic_accuracy(db, user)


@router.get("/progress", response_model=list[schemas.ProgressItem])
def progress(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return analytics.progress(db, user)


@router.get("/history")
def history(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    return history_service.history(db, user, limit=limit)

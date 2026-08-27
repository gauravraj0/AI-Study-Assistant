from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import auth as auth_service
from ..services import qa

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=list[schemas.ChatSessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    out = []
    for s in qa.list_sessions(db, user):
        item = schemas.ChatSessionOut.model_validate(s)
        item.message_count = len(s.messages)
        out.append(item)
    return out


@router.post("/sessions", response_model=schemas.ChatSessionOut, status_code=201)
def create_session(
    body: schemas.ChatSessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        s = qa.create_session(db, user, body.document_id, body.title)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return schemas.ChatSessionOut.model_validate(s)


@router.get("/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        s = qa.get_session_detail(db, user, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return s


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        qa.delete_session(db, user, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None


@router.post("/sessions/{session_id}/messages", response_model=schemas.MessageOut)
def post_message(
    session_id: int,
    body: schemas.MessageIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth_service.get_current_user),
):
    try:
        s = qa.get_session(db, user, session_id)
        msg = qa.ask(db, user, s, body.content, mode=body.mode)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return msg

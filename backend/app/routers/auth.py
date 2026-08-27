from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register(db, body.email, body.name, body.password)
    return auth_service.issue_token(user)


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.login(db, body.email, body.password)
    return auth_service.issue_token(user)


@router.post("/firebase", response_model=schemas.TokenResponse)
def firebase(body: schemas.FirebaseLoginRequest, db: Session = Depends(get_db)):
    user = auth_service.firebase_login(db, body.id_token)
    return auth_service.issue_token(user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(auth_service.get_current_user)):
    return user

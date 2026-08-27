"""Authentication: local email/password (JWT) + optional Firebase ID tokens.

The Firebase path activates when ``FIREBASE_SERVICE_ACCOUNT_FILE`` points at a
service-account JSON (and the optional ``firebase-admin`` package is installed).
"""

import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..database import get_db
from ..security import create_access_token, decode_access_token, hash_password, verify_password

log = logging.getLogger("aisa.auth")

_bearer = HTTPBearer(auto_error=False)

#: Cookie name used as a fallback token channel (set by the frontend).
TOKEN_COOKIE = "aisa_token"

_firebase_auth = None


def _extract_token(request: Request, creds: HTTPAuthorizationCredentials | None) -> str:
    """Return the presented JWT from whichever channel survived the network.

    The standard ``Authorization: Bearer`` header is preferred, but some
    preview/proxy layers silently drop it. The frontend therefore also sends
    the token as an ``X-Api-Token`` header and in the ``aisa_token`` cookie,
    and any of the three is accepted here.
    """
    if creds and creds.credentials:
        return creds.credentials
    return request.headers.get("x-api-token") or request.cookies.get(TOKEN_COOKIE) or ""


def _get_firebase_auth():
    """Lazily initialise firebase-admin (only when configured)."""
    global _firebase_auth
    if _firebase_auth is None and settings.firebase_enabled:
        try:
            import firebase_admin
            from firebase_admin import credentials, auth as fauth

            if not firebase_admin._apps:
                firebase_admin.initialize_app(
                    credentials.Certificate(settings.firebase_service_account_file)
                )
            _firebase_auth = fauth
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Firebase is configured but unavailable: {e}. Install backend/requirements-optional.txt",
            )
    return _firebase_auth


def register(db: Session, email: str, name: str, password: str) -> models.User:
    existing = db.query(models.User).filter(models.User.email == email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = models.User(email=email.lower(), name=name, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email.lower()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return user


def firebase_login(db: Session, id_token: str) -> models.User:
    fauth = _get_firebase_auth()
    if fauth is None:
        raise HTTPException(status_code=400, detail="Firebase auth is not configured on this server.")
    try:
        claims = fauth.verify_id_token(id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token.")
    uid = claims.get("uid", "")
    email = (claims.get("email") or f"{uid}@firebase.user").lower()
    name = claims.get("name") or claims.get("email") or "Firebase User"
    user = db.query(models.User).filter((models.User.firebase_uid == uid) | (models.User.email == email)).first()
    if user is None:
        user = models.User(email=email, name=name, firebase_uid=uid)
        db.add(user)
    elif user.firebase_uid is None:
        user.firebase_uid = uid
    db.commit()
    db.refresh(user)
    return user


def issue_token(user: models.User) -> dict:
    return {"access_token": create_access_token(user.id, user.email), "token_type": "bearer", "user": user}


def _reject(reason: str, token: str = "") -> HTTPException:
    # Diagnostic logging: tells us exactly *why* a browser request 401'd.
    log.warning("auth rejected: %s (token prefix %r)", reason, (token or "")[:25])
    return HTTPException(status_code=401, detail=reason, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    token = _extract_token(request, creds)
    if not token:
        raise _reject(
            "No token found (checked Authorization header, X-Api-Token header, "
            f"and {TOKEN_COOKIE} cookie)."
        )
    try:
        payload = decode_access_token(token)
        user = db.get(models.User, int(payload.get("sub", "0")))
    except Exception as e:  # noqa: BLE001
        raise _reject(f"Invalid or expired token ({type(e).__name__}).", token)
    if user is None:
        raise _reject("User no longer exists (token refers to a deleted account).", token)
    # Defense in depth: numeric ids can be recycled after a user is deleted;
    # the email binding prevents a stale token from authenticating as a
    # different (later) user that reuses the same id.
    if payload.get("email") and payload["email"] != user.email:
        raise _reject(
            f"Token does not match this account (token email {payload.get('email')!r} != "
            f"user email {user.email!r}).",
            token,
        )
    return user

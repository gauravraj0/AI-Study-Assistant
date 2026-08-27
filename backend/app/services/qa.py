"""RAG chat: session management + ask/explain with retrieval."""

from sqlalchemy.orm import Session, selectinload

from .. import models
from ..llm import get_provider
from ..rag import retrieve
from .activity import log_activity


def create_session(db: Session, user: models.User, document_id: int | None, title: str | None) -> models.ChatSession:
    if document_id:
        doc = db.get(models.Document, document_id)
        if doc is None or doc.user_id != user.id:
            raise ValueError("Document not found.")
    s = models.ChatSession(user_id=user.id, document_id=document_id, title=(title or "").strip() or "New conversation")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_session(db: Session, user: models.User, session_id: int) -> models.ChatSession:
    s = db.get(models.ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise ValueError("Session not found.")
    return s


def list_sessions(db: Session, user: models.User) -> list[models.ChatSession]:
    return (
        db.query(models.ChatSession)
        .options(selectinload(models.ChatSession.messages))
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )


def get_session_detail(db: Session, user: models.User, session_id: int) -> models.ChatSession:
    s = db.get(models.ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise ValueError("Session not found.")
    return s


def ask(
    db: Session,
    user: models.User,
    session: models.ChatSession,
    content: str,
    mode: str = "ask",
) -> models.ChatMessage:
    db.add(models.ChatMessage(session_id=session.id, role="user", content=content, mode=mode))
    if session.title == "New conversation":
        session.title = content[:60]
    db.commit()

    if session.document_id:
        doc_ids = [session.document_id]
    else:
        doc_ids = [d.id for d in db.query(models.Document).filter(models.Document.user_id == user.id).all()]

    contexts = retrieve(doc_ids, content, k=5)
    provider = get_provider()
    if not contexts:
        answer = (
            "There's no uploaded material to draw from yet. Upload a document (PDF, DOCX, TXT or MD) "
            "and I can answer questions about it."
        )
    elif mode == "explain":
        answer = provider.explain(content, contexts)
    else:
        answer = provider.answer(content, contexts)

    msg = models.ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(msg)
    log_activity(db, user, "chat_question", session.document_id, f"{mode.upper()}: {content[:100]}")
    db.commit()
    db.refresh(msg)
    return msg


def delete_session(db: Session, user: models.User, session_id: int) -> None:
    s = db.get(models.ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise ValueError("Session not found.")
    db.delete(s)
    db.commit()

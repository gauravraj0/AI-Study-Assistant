"""Seed a demo account + sample documents on first start (SEED_DEMO=true).

Gives new users something to explore immediately: login as
``demo@study.ai`` / ``demo1234`` and find two processed study documents.
"""

import logging
import os

from .config import settings
from .database import SessionLocal
from .models import Activity, Document, User
from .security import hash_password
from .services import documents as doc_service

log = logging.getLogger("aisa.seed")

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def _ingest_file(db, user: User, path: str, name: str) -> None:
    with open(path, "rb") as fh:
        content = fh.read()
    doc = Document(user_id=user.id, original_name=name, file_type=os.path.splitext(path)[1].lstrip(".").lower(), status="processing")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    try:
        text, pages = doc_service._extract(content, doc.file_type)
        chunks = doc_service.chunk_text(text)
        from .llm import get_embedder, get_provider
        from .rag import get_vector_store

        vectors = get_embedder().embed(chunks)
        store = get_vector_store()
        store.add(doc.id, [{"id": f"doc{doc.id}-c{i}", "text": c, "meta": {"index": i, "source": name}} for i, c in enumerate(chunks)], vectors)
        doc.num_pages = pages
        doc.num_chunks = len(chunks)
        doc.status = "ready"
        doc.summary = get_provider().summarize(text)
        db.add(Activity(user_id=user.id, type="document_uploaded", document_id=doc.id, detail=f"Seeded sample: {name}"))
        db.commit()
        log.info("seeded document %s (%d chunks)", name, len(chunks))
    except Exception as e:  # noqa: BLE001
        doc.status = "error"
        doc.error = str(e)
        db.commit()
        log.warning("failed to seed %s: %s", name, e)


def seed_demo() -> None:
    if not settings.seed_demo:
        return
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@study.ai").first():
            return
        user = User(email="demo@study.ai", name="Demo Student", password_hash=hash_password("demo1234"))
        db.add(user)
        db.commit()
        db.refresh(user)
        log.info("seeded demo user demo@study.ai / demo1234")

        pdf = os.path.join(ASSETS, "machine_learning_fundamentals.pdf")
        md = os.path.join(ASSETS, "cell_biology_notes.md")
        if os.path.exists(pdf):
            _ingest_file(db, user, pdf, "machine_learning_fundamentals.pdf")
        if os.path.exists(md):
            _ingest_file(db, user, md, "cell_biology_notes.md")
    finally:
        db.close()

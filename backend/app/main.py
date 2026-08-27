"""AI Study Assistant — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .llm import get_provider
from .routers import analytics, auth, chat, documents, flashcards, plans, quizzes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aisa")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    from .seed import seed_demo

    seed_demo()
    log.info("AI Study Assistant ready (llm=%s)", get_provider().name)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered learning platform: upload material, chat with a RAG tutor, "
    "generate quizzes/flashcards/study plans, track progress.",
    lifespan=lifespan,
)

origins = ["*"] if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(quizzes.router)
app.include_router(flashcards.router)
app.include_router(plans.router)
app.include_router(analytics.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version, "llm_provider": get_provider().name}


@app.get("/api/config", tags=["meta"])
def public_config():
    """Non-secret client config (used by the frontend)."""
    return {
        "llm_provider": get_provider().name,
        "firebase_enabled": settings.firebase_enabled,
        "voice_input": True,  # Web Speech API in the browser
        "supported_uploads": ["pdf", "docx", "txt", "md", "csv", "json"],
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
    }

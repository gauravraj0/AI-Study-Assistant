# 🎓 AI Study Assistant

An AI-powered learning platform. Upload your study material, and an intelligent tutor
built on **Retrieval-Augmented Generation (RAG)** answers questions, explains concepts,
generates MCQ quizzes, flashcard decks and personalised study plans — while tracking
your progress and performance.

Built with **Python · FastAPI · React · PostgreSQL · Vector search · Firebase (optional) · Generative AI**.

---

## ✨ Features

| Area | What it does |
|---|---|
| **Document upload** | PDF, DOCX, TXT, MD, CSV, JSON — parsed, chunked, embedded and indexed |
| **AI summarization** | One-click summaries of every document (regenerable) |
| **AI tutor chat** | Ask questions over *all* your documents (RAG) or scope one conversation to a single document; **Ask** and **Explain** modes |
| **Voice questions** | Speak your question to the tutor (Web Speech API) and hear answers read aloud |
| **MCQ generation** | Automatic multiple-choice questions from any document, with **easy / medium / hard** difficulty |
| **Quiz engine** | Timed self-graded quizzes, per-question AI explanations on the results screen |
| **Flashcards** | Auto-generated decks (definitions + fill-in-the-blank) with spaced-repetition review (Again / Good / Easy) |
| **AI explanations** | Deep-dive explanations for any question or quiz item |
| **Study plans** | Personalised 5-day plans built from your documents and recent quiz scores |
| **Progress tracking** | Per-document progress (processed → summarized → quizzed → reviewed) |
| **Performance analytics** | Score trend, accuracy by topic, pass rate, day streak, activity feed |
| **Study history** | Full timeline of every study action |
| **Auth** | Local email/password (JWT) out of the box; **Firebase Auth** when configured |

## 🏗️ Architecture

```
┌───────────────────────────  React (Vite)  ───────────────────────────┐
│  Dashboard · Documents · Chat(voice) · Quizzes · Flashcards · Plans  │
│  Analytics (Recharts) · History        Bearer token in localStorage  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ /api (proxied)
┌──────────────────────────────────▼───────────────────────────────────┐
│                        FastAPI backend                               │
│                                                                      │
│  Routers: auth · documents · chat · quizzes · flashcards · plans ·   │
│           analytics · history                                        │
│                                                                      │
│  Services                                                            │
│  ├─ documents: pypdf / python-docx extraction → chunker (900ch,     │
│  │              120 overlap) → embed → vector store                  │
│  ├─ qa:        hybrid retrieval (cosine + BM25-lite) → LLM answer   │
│  ├─ quizzes:   MCQ generation (difficulty-aware) + scoring          │
│  ├─ flashcards: pattern mining + SM-2-lite spaced repetition        │
│  └─ plans/analytics/history: profile → plan, aggregates, timeline   │
│                                                                      │
│  LLM layer (pluggable provider, auto-selected)                       │
│  ├─ local    → key-free engine: extractive summarization,           │
│  │             sentence-relevance Q&A, fact-based MCQs with mutated  │
│  │             distractors, definition flashcards, plan templates    │
│  ├─ openai   → GPT chat/completions + embeddings (REST via httpx)   │
│  └─ gemini   → Gemini generateContent + embeddings (REST via httpx) │
│           (remote providers auto-fall back to local on failure)      │
│                                                                      │
│  Storage                                                             │
│  ├─ SQLAlchemy ORM → SQLite by default, PostgreSQL via DATABASE_URL │
│  └─ Persistent vector store (numpy cosine partitions, swappable     │
│     interface for Chroma / pgvector)                                │
└──────────────────────────────────────────────────────────────────────┘
```

**RAG pipeline:** `document → extract → chunk → embed → store` and
`question → embed → hybrid retrieve (cosine 45% + BM25 55%) → top-5 contexts → provider.answer/explain`.

## 🚀 Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On first start it seeds a demo account: **`demo@study.ai` / `demo1234`** with two
processed sample documents (machine-learning PDF + cell-biology notes).
Set `SEED_DEMO=false` to disable.

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → :8000)
```

Sign in with the demo account and start asking.

### 3. Tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

One end-to-end smoke test covers: auth → upload → RAG chat → quiz generation &
submission → flashcards + review → study plan → analytics → progress → history → delete.

### 4. Docker (full stack with PostgreSQL)

```bash
docker compose up --build
```

Brings up Postgres 16 + FastAPI + React dev server; the backend uses
`DATABASE_URL=postgresql+psycopg2://study:study@db:5432/study`.
(Install `backend/requirements-optional.txt` for the postgres driver + firebase.)

## 🔑 Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | Any SQLAlchemy URL — e.g. `postgresql+psycopg2://…` |
| `JWT_SECRET` | dev value | **Change in production** |
| `LLM_PROVIDER` | `auto` | `auto` \| `openai` \| `gemini` \| `local` |
| `OPENAI_API_KEY` | — | Enables GPT chat + embeddings (auto-selected when set) |
| `OPENAI_MODEL` / `OPENAI_EMBED_MODEL` | `gpt-4o-mini` / `text-embedding-3-small` | |
| `GEMINI_API_KEY` | — | Enables Gemini chat + embeddings |
| `GEMINI_MODEL` | `gemini-1.5-flash` | |
| `FIREBASE_SERVICE_ACCOUNT_FILE` | — | Path to service-account JSON → enables Firebase ID-token login |
| `DATA_DIR` / `VECTOR_STORE_PATH` | `./data` | SQLite + vector partition storage |
| `CORS_ORIGINS` | `*` | Comma-separated allow-list |
| `SEED_DEMO` | `true` | Seed demo user + sample documents |
| `MAX_UPLOAD_BYTES` | 25 MB | Upload cap |

Create a `backend/.env` file with any of the above (it is git-ignored).

### Token transport

The frontend stores the JWT in `localStorage` and sends it as
`Authorization: Bearer …`. Because some preview/proxy layers silently drop the
`Authorization` header, the token is **also** sent as an `X-Api-Token` header
and in a `SameSite=Lax` `aisa_token` cookie; the backend accepts whichever
channel arrives (`services/auth.py:_extract_token`). After login the app
verifies the fresh token with `GET /api/auth/me` and hard-reloads on success —
the error surfaced to the user includes the server's exact rejection reason.

### AI engine behaviour

* **No keys (default):** the deterministic **local engine** powers everything —
  extractive summarization, relevance-ranked RAG answers, fact-sentence MCQs
  (hard difficulty mutates numbers/terms to build distractors), definition +
  fill-in-the-blank flashcards, and topic-driven study plans. Great for
  development, demos and offline use.
* **With `OPENAI_API_KEY` or `GEMINI_API_KEY`:** generation upgrades to the real
  LLM automatically (JSON-structured MCQs/flashcards/plans, grounded answers),
  with per-task fallback to the local engine if a call fails.

### Firebase auth

1. `pip install -r backend/requirements-optional.txt`
2. Export a service-account JSON, set `FIREBASE_SERVICE_ACCOUNT_FILE=/path/sa.json`
3. The frontend calls `POST /api/auth/firebase` with the Firebase ID token;
   the backend verifies it with `firebase-admin` and upserts the user.

## 📁 Repository layout

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, lifespan (init + demo seed)
│   ├── config.py          # pydantic-settings
│   ├── database.py        # SQLAlchemy engine/session
│   ├── models.py          # ORM: User, Document, Chat*, Quiz*, Flashcard*, StudyPlan, Activity
│   ├── schemas.py         # Pydantic request/response models
│   ├── security.py        # PBKDF2 password hashing + JWT
│   ├── llm/               # provider layer: base · local · remote(openai/gemini) · embeddings
│   ├── rag/               # vector store (persistent partitions) + hybrid retriever
│   ├── services/          # documents · qa · quizzes · flashcards · plans · analytics · auth
│   ├── routers/           # REST endpoints
│   └── seed.py            # demo account + sample documents
├── assets/                # sample ML PDF (generated by tools/) + cell-biology notes
├── tools/make_sample_pdf.py
├── tests/test_smoke.py    # end-to-end API smoke test
└── requirements*.txt
frontend/
├── vite.config.js         # dev server + /api proxy
└── src/
    ├── api.js · auth.jsx · hooks.js (voice + TTS)
    ├── components/        # Layout, UI kit
    └── pages/             # Login, Dashboard, Documents(+detail), Chat, Quizzes,
                           # QuizTake, QuizReview, Flashcards(+set), Plans, Analytics, History
docker-compose.yml         # Postgres + backend + frontend
```

## 🗺️ Swapping in production-grade infrastructure

* **Vector DB:** `rag/vector_store.py` exposes `add / search / delete` per
  document partition — mirror it with Chroma or Postgres `pgvector` and point
  `retriever.py` at it.
* **PostgreSQL:** just set `DATABASE_URL` (models are portable SQLAlchemy).
* **Auth:** Firebase path is already implemented; add Google/SSO the same way.
* **Async ingestion:** document processing is synchronous today; move
  `services/documents.ingest_document` into a task queue (Celery/ARQ) for large files.

## 📄 License

MIT

"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth -------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class FirebaseLoginRequest(BaseModel):
    id_token: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- documents ----------------------------------------------------------------
class DocumentOut(ORMModel):
    id: int
    original_name: str
    file_type: str
    num_pages: int
    num_chunks: int
    status: str
    error: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    quiz_count: int = 0
    flashcard_count: int = 0


class ReSummarizeRequest(BaseModel):
    max_words: int = Field(default=180, ge=40, le=800)


# --- chat --------------------------------------------------------------------
class ChatSessionCreate(BaseModel):
    document_id: Optional[int] = None
    title: Optional[str] = None


class ChatSessionOut(ORMModel):
    id: int
    document_id: Optional[int]
    title: str
    created_at: datetime
    message_count: int = 0


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    mode: Literal["ask", "explain"] = "ask"


class MessageOut(ORMModel):
    id: int
    role: str
    content: str
    mode: Optional[str]
    created_at: datetime


class ChatSessionDetail(ORMModel):
    id: int
    document_id: Optional[int]
    title: str
    created_at: datetime
    messages: list[MessageOut]


# --- quizzes -------------------------------------------------------------------
class QuizGenerateRequest(BaseModel):
    document_id: int
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    count: int = Field(default=5, ge=3, le=15)


class QuizQuestionOut(ORMModel):
    id: int
    idx: int
    topic: str
    question: str
    options: list[str]
    explanation: str
    difficulty: str
    correct_index: Optional[int] = None  # only when include_answers=True
    your_answer: Optional[int] = None  # only on the results view


class QuizOut(ORMModel):
    id: int
    document_id: Optional[int]
    document_name: Optional[str] = None
    difficulty: str
    title: str
    num_questions: int
    score: Optional[int]
    passed: Optional[bool]
    submitted_at: Optional[datetime]
    created_at: datetime


class QuizDetail(BaseModel):
    quiz: QuizOut
    questions: list[QuizQuestionOut]
    results: Optional[list[dict]] = None


class QuizSubmitRequest(BaseModel):
    answers: list[int]


# --- flashcards ------------------------------------------------------------------
class FlashcardGenerateRequest(BaseModel):
    document_id: int
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    count: int = Field(default=10, ge=4, le=30)


class FlashcardSetOut(ORMModel):
    id: int
    document_id: Optional[int]
    document_name: Optional[str] = None
    difficulty: str
    title: str
    created_at: datetime
    card_count: int = 0
    reviewed_count: int = 0


class FlashcardOut(ORMModel):
    id: int
    idx: int
    front: str
    back: str
    times_seen: int
    interval_days: float
    last_reviewed: Optional[datetime]


class FlashcardReviewRequest(BaseModel):
    quality: Literal[0, 1, 2]  # 0=again, 1=good, 2=easy


# --- study plans -------------------------------------------------------------------
class StudyPlanOut(ORMModel):
    id: int
    title: str
    goal: str
    total_days: int
    days: list
    created_at: datetime


# --- analytics / history / progress ---------------------------------------------------
class ScorePoint(BaseModel):
    date: str
    score: int
    title: str
    difficulty: str


class TopicAccuracy(BaseModel):
    topic: str
    answered: int
    correct: int
    accuracy: float


class OverviewStats(BaseModel):
    documents: int
    ready_documents: int
    quizzes: int
    submitted_quizzes: int
    average_score: Optional[float]
    pass_rate: Optional[float]
    flashcards_reviewed: int
    flashcards_total: int
    chat_messages: int
    streak_days: int
    recent_activity: list[dict]


class ProgressItem(BaseModel):
    document_id: int
    document_name: str
    status: str
    progress_pct: float
    quizzes: int
    best_score: Optional[int]
    flashcards_total: int
    flashcards_reviewed: int
    chat_messages: int
    last_activity: Optional[datetime]

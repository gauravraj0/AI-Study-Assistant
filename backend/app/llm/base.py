"""Provider interface.

Every provider implements the same task-oriented API so the rest of the app
never has to know *how* the text is produced. ``contexts`` is a list of
retrieved chunks: ``[{"text": str, "score": float, "source": str, "meta": dict}]``.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class MCQ:
    question: str
    options: list[str]
    correct_index: int
    explanation: str
    topic: str = ""
    difficulty: str = "medium"


@dataclass
class Flashcard:
    front: str
    back: str


@dataclass
class Context:
    text: str
    score: float = 0.0
    source: str = ""
    meta: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    def summarize(self, text: str, max_words: int = 180) -> str: ...
    def answer(self, question: str, contexts: list[Context]) -> str: ...
    def explain(self, question: str, contexts: list[Context]) -> str: ...
    def generate_mcqs(self, contexts: list[Context], count: int = 5, difficulty: str = "medium") -> list[MCQ]: ...
    def generate_flashcards(self, contexts: list[Context], count: int = 10, difficulty: str = "medium") -> list[Flashcard]: ...
    def generate_study_plan(self, profile: dict[str, Any]) -> dict: ...


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

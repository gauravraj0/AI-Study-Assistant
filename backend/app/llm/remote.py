"""OpenAI + Gemini providers.

They call the vendor REST APIs directly with ``httpx`` (no SDK dependency) and
transparently fall back to the local engine if a call fails, so the app never
breaks because of a network/API hiccup.
"""

import json
import logging
import re

import httpx

from .base import Context, Flashcard, MCQ
from .local import LocalProvider

log = logging.getLogger("aisa.llm")

_TIMEOUT = httpx.Timeout(90.0, connect=10.0)


def _loads_lenient(content: str):
    """Parse JSON from an LLM reply, tolerating code fences and chatter."""
    s = content.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        pass
    for opener, closer in (("[", "]"), ("{", "}")):
        start = s.find(opener)
        end = s.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                continue
    return None


_MCQ_SYSTEM = (
    "You are an expert exam question writer for students. You respond ONLY with valid JSON, "
    "no markdown, no commentary."
)


class _RemoteBase:
    name = "remote"

    def __init__(self, fallback: LocalProvider):
        self._local = fallback
        self._client = httpx.Client(timeout=_TIMEOUT)

    # helpers each vendor implements
    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        raise NotImplementedError

    def _embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    # --- task implementations -------------------------------------------------
    def summarize(self, text: str, max_words: int = 180) -> str:
        user = (
            f"Summarize the following study material in at most {max_words} words. Keep key "
            "terms, definitions, and numbers. Write 2-4 concise paragraphs.\n\n" + text[:24000]
        )
        try:
            return self._chat("You are a study assistant that writes clear, accurate summaries.", user)
        except Exception as e:
            log.warning("openai/gemini summarize failed (%s); using local engine", e)
            return self._local.summarize(text, max_words)

    def answer(self, question: str, contexts: list[Context]) -> str:
        if not contexts:
            return self._local.answer(question, contexts)
        ctx = "\n\n".join(f"[{i + 1}] {c.text}" for i, c in enumerate(contexts))
        system = (
            "You are a study tutor. Answer ONLY using the provided context excerpts. Cite the "
            "excerpt number like [1]. If the answer is not in the context, say so clearly."
        )
        user = f"Context:\n{ctx}\n\nStudent question: {question}"
        try:
            return self._chat(system, user)
        except Exception as e:
            log.warning("remote answer failed (%s); using local engine", e)
            return self._local.answer(question, contexts)

    def explain(self, question: str, contexts: list[Context]) -> str:
        if not contexts:
            return self._local.explain(question, contexts)
        ctx = "\n\n".join(c.text for c in contexts[:4])
        system = (
            "You are a patient study tutor. Explain the concept behind the student's question "
            "using ONLY the provided context. Use short sections with bullet points and end "
            "with one concrete study tip."
        )
        user = f"Context:\n{ctx}\n\nExplain this: {question}"
        try:
            return self._chat(system, user)
        except Exception as e:
            log.warning("remote explain failed (%s); using local engine", e)
            return self._local.explain(question, contexts)

    def generate_mcqs(self, contexts: list[Context], count: int = 5, difficulty: str = "medium") -> list[MCQ]:
        ctx = "\n\n---\n\n".join(c.text for c in contexts[:16])
        user = (
            f"Create exactly {count} multiple-choice questions from this material.\n"
            f"Difficulty: {difficulty} (easy = direct recall, medium = comprehension, hard = "
            "application/inference with tricky distractors).\n"
            f"Respond with a JSON array of objects: "
            '[{"question": str, "options": [4 strings], "correct_index": 0-3, '
            '"explanation": str, "topic": short keyword}]'
            f"\n\nMaterial:\n{ctx[:24000]}"
        )
        try:
            data = self._chat(_MCQ_SYSTEM, user, json_mode=True)
            parsed = _loads_lenient(data) if isinstance(data, str) else data
            mcqs: list[MCQ] = []
            for item in parsed if isinstance(parsed, list) else []:
                opts = item.get("options") or []
                ci = int(item.get("correct_index", 0))
                if len(opts) == 4 and 0 <= ci < 4 and item.get("question"):
                    mcqs.append(
                        MCQ(
                            question=str(item["question"]),
                            options=[str(o) for o in opts],
                            correct_index=ci,
                            explanation=str(item.get("explanation", "")),
                            topic=str(item.get("topic", ""))[:80],
                            difficulty=difficulty,
                        )
                    )
            if len(mcqs) >= 3:
                return mcqs[:count]
        except Exception as e:
            log.warning("remote MCQ generation failed (%s); using local engine", e)
        return self._local.generate_mcqs(contexts, count, difficulty)

    def generate_flashcards(self, contexts: list[Context], count: int = 10, difficulty: str = "medium") -> list[Flashcard]:
        ctx = "\n\n---\n\n".join(c.text for c in contexts[:16])
        user = (
            f"Create {count} study flashcards from this material. Difficulty: {difficulty} "
            "(easy = short definitions, hard = inference and application).\n"
            f'Respond with a JSON array: [{"front": str, "back": str}]'
            f"\n\nMaterial:\n{ctx[:24000]}"
        )
        try:
            data = self._chat(_MCQ_SYSTEM, user, json_mode=True)
            parsed = _loads_lenient(data) if isinstance(data, str) else data
            cards = [
                Flashcard(front=str(c["front"]), back=str(c["back"]))
                for c in (parsed if isinstance(parsed, list) else [])
                if c.get("front") and c.get("back")
            ]
            if len(cards) >= 4:
                return cards[:count]
        except Exception as e:
            log.warning("remote flashcard generation failed (%s); using local engine", e)
        return self._local.generate_flashcards(contexts, count, difficulty)

    def generate_study_plan(self, profile: dict) -> dict:
        user = (
            "Create a personalised 5-day study plan for this student.\n"
            f"Profile (JSON): {json.dumps(profile)[:6000]}\n"
            "Respond with JSON: {\"title\": str, \"goal\": str, \"total_days\": 5, "
            '"days": [{"day": int, "focus": str, "tasks": [str]}]}'
        )
        try:
            data = self._chat(
                "You are a study coach who plans efficient, specific study schedules.", user, json_mode=True
            )
            parsed = _loads_lenient(data) if isinstance(data, str) else data
            if isinstance(parsed, dict) and parsed.get("days"):
                parsed.setdefault("total_days", 5)
                parsed.setdefault("title", "Personalised study plan")
                parsed.setdefault("goal", "Master your material")
                return parsed
        except Exception as e:
            log.warning("remote study plan failed (%s); using local engine", e)
        return self._local.generate_study_plan(profile)


class OpenAIProvider(_RemoteBase):
    name = "openai"

    def __init__(self, api_key: str, model: str, embed_model: str, fallback: LocalProvider):
        super().__init__(fallback)
        self.api_key = api_key
        self.model = model
        self.embed_model = embed_model

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        payload = {"model": self.model, "temperature": 0.2, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        r = self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        r = self._client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.embed_model, "input": texts[:2048]},
        )
        r.raise_for_status()
        data = r.json()["data"]
        return [d["embedding"] for d in data]


class GeminiProvider(_RemoteBase):
    name = "gemini"

    EMBED_MODEL = "text-embedding-004"

    def __init__(self, api_key: str, model: str, fallback: LocalProvider):
        super().__init__(fallback)
        self.api_key = api_key
        self.model = model

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
        body: dict = {
            "systemInstruction": {"parts": [{"text": system + (" Respond with JSON only." if json_mode else "")}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2},
        }
        r = self._client.post(url, params={"key": self.api_key}, json=body)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        base = "https://generativelanguage.googleapis.com/v1/models"
        for t in texts[:2048]:
            r = self._client.post(
                f"{base}/{self.EMBED_MODEL}:embedContent",
                params={"key": self.api_key},
                json={"model": f"models/{self.EMBED_MODEL}", "content": {"parts": [{"text": t[:2000]}]}},
            )
            r.raise_for_status()
            out.append(r.json()["embedding"]["values"])
        return out

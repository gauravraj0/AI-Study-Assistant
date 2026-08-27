"""Embedding functions: local hashed vectorizer (no keys needed) plus
OpenAI / Gemini embeddings when an API key is configured."""

import hashlib
import math



class LocalEmbedder:
    """Signed hashed bag-of-words vectorizer.

    Deterministic, dependency-free, and surprisingly effective for lexical
    retrieval over study material. Swap for a real embedding model by setting
    ``OPENAI_API_KEY`` / ``GEMINI_API_KEY``.
    """

    name = "local-hash"
    dim = 1024

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        text = text.lower()
        toks = []
        for m in __import__("re").finditer(r"[a-z][a-z0-9\-']*", text):
            w = m.group(0)
            if len(w) >= 3:
                toks.append(w)
        # unigrams + bigrams for a bit of phrase sensitivity
        grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        for g in grams:
            h = int.from_bytes(hashlib.sha256(g.encode()).digest()[:8], "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
            v[idx] += sign
        norm = math.sqrt(sum(x * x for x in v))
        if norm > 0:
            v = [x / norm for x in v]
        return v

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class OpenAIEmbedder:
    name = "openai"

    def __init__(self, api_key: str, model: str, dim: int = 1536, fallback: LocalEmbedder | None = None):
        import httpx

        self._client = httpx.Client(timeout=90.0)
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self._fallback = fallback or LocalEmbedder()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            out: list[list[float]] = []
            for i in range(0, len(texts), 200):
                batch = texts[i : i + 200]
                r = self._client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": batch},
                )
                r.raise_for_status()
                out.extend(d["embedding"] for d in r.json()["data"])
            return out
        except Exception:
            return self._fallback.embed(texts)


class GeminiEmbedder:
    name = "gemini"
    MODEL = "text-embedding-004"

    def __init__(self, api_key: str, fallback: LocalEmbedder | None = None):
        import httpx

        self._client = httpx.Client(timeout=90.0)
        self.api_key = api_key
        self.dim = 768
        self._fallback = fallback or LocalEmbedder()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            out: list[list[float]] = []
            base = "https://generativelanguage.googleapis.com/v1/models"
            for t in texts:
                r = self._client.post(
                    f"{base}/{self.MODEL}:embedContent",
                    params={"key": self.api_key},
                    json={"model": f"models/{self.MODEL}", "content": {"parts": [{"text": t[:2000]}]}},
                )
                r.raise_for_status()
                out.append(r.json()["embedding"]["values"])
            return out
        except Exception:
            return self._fallback.embed(texts)

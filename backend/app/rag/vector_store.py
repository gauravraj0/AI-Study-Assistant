"""Persistent embedded vector store (numpy + JSON partitions).

One JSON partition per document: ``<store_path>/doc_<id>.json`` containing ids,
texts, metadata and vectors. Search is brute-force cosine similarity, which is
fast and exact at study-material scale (thousands of chunks).

The interface (add / search / delete) is intentionally close to Chroma or
pgvector so swapping in a production vector database is a drop-in change.
"""

import json
import os
import threading

import numpy as np

from ..config import settings


class VectorStore:
    def __init__(self, path: str | None = None):
        self.path = path or settings.resolved_vector_path
        os.makedirs(self.path, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[int, dict] = {}

    def _file(self, doc_id: int) -> str:
        return os.path.join(self.path, f"doc_{doc_id}.json")

    def _load(self, doc_id: int) -> dict | None:
        if doc_id in self._cache:
            return self._cache[doc_id]
        f = self._file(doc_id)
        if not os.path.exists(f):
            return None
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data["vectors"] = np.asarray(data.pop("_vectors"), dtype=np.float32)
        self._cache[doc_id] = data
        return data

    def _save(self, doc_id: int, data: dict) -> None:
        vectors = data.pop("vectors", None)
        payload = {
            "ids": data["ids"],
            "texts": data["texts"],
            "metas": data["metas"],
            "_vectors": vectors.tolist() if vectors is not None else [],
        }
        with open(self._file(doc_id), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        data["vectors"] = vectors
        self._cache[doc_id] = data

    def add(self, doc_id: int, items: list[dict], vectors: list[list[float]]) -> None:
        """items: [{id, text, meta}]; vectors aligned with items."""
        with self._lock:
            data = self._load(doc_id) or {"ids": [], "texts": [], "metas": [], "vectors": np.zeros((0,), dtype=np.float32)}
            data["ids"].extend(it["id"] for it in items)
            data["texts"].extend(it["text"] for it in items)
            data["metas"].extend(it.get("meta", {}) for it in items)
            arr = np.asarray(vectors, dtype=np.float32)
            data["vectors"] = arr if data["vectors"].size == 0 else np.vstack([data["vectors"], arr])
            self._save(doc_id, data)

    def search(self, doc_id: int, vector: list[float], k: int = 5) -> list[dict]:
        data = self._load(doc_id)
        if not data or data["vectors"].size == 0:
            return []
        v = np.asarray(vector, dtype=np.float32).reshape(-1)
        norms = np.linalg.norm(data["vectors"], axis=1)
        norms[norms == 0] = 1.0
        qn = float(np.linalg.norm(v)) or 1.0
        scores = (data["vectors"] @ v) / (norms * qn)
        idx = np.argsort(scores)[::-1][:k].tolist()
        return [
            {
                "id": data["ids"][i],
                "text": data["texts"][i],
                "meta": data["metas"][i],
                "score": float(scores[i]),
            }
            for i in idx
        ]

    def all_chunks(self, doc_id: int, limit: int = 200) -> list[dict]:
        data = self._load(doc_id)
        if not data:
            return []
        out = [
            {"id": data["ids"][i], "text": data["texts"][i], "meta": data["metas"][i], "score": 0.0}
            for i in range(len(data["texts"]))
        ]
        # even sample if huge
        if len(out) > limit:
            step = len(out) / limit
            out = [out[int(i * step)] for i in range(limit)]
        return out

    def delete(self, doc_id: int) -> None:
        with self._lock:
            self._cache.pop(doc_id, None)
            f = self._file(doc_id)
            if os.path.exists(f):
                os.remove(f)

    def has(self, doc_id: int) -> bool:
        return self._load(doc_id) is not None


_store: VectorStore | None = None
_store_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = VectorStore()
        return _store

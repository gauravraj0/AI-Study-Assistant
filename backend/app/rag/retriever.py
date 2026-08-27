"""RAG retrieval: hybrid scoring.

Combines (a) cosine similarity in the vector store with (b) a lightweight BM25
lexical score over the same candidate chunks. The blend makes retrieval robust
even with the key-free hashed local embedder, and it only gets better when a
real embedding model is configured.
"""

import math

from ..llm import get_embedder
from ..llm.base import Context
from ..llm.local import STOPWORDS, tokens
from .vector_store import get_vector_store

_CANDIDATES_PER_DOC = 30


def _bm25_scores(query: str, chunks: list[dict]) -> list[float]:
    n = len(chunks)
    if n == 0:
        return []
    doc_tokens = [tokens(c["text"]) for c in chunks]
    df: dict[str, int] = {}
    counts: list[dict[str, int]] = []
    for dt in doc_tokens:
        freq: dict[str, int] = {}
        for t in dt:
            freq[t] = freq.get(t, 0) + 1
        counts.append(freq)
        for t in freq:
            df[t] = df.get(t, 0) + 1
    scores = [0.0] * n
    for qt in set(tokens(query)):
        if qt in STOPWORDS or len(qt) < 3 or qt not in df:
            continue
        idf = math.log(1 + (n - df[qt] + 0.5) / (df[qt] + 0.5))
        for i, freq in enumerate(counts):
            f = freq.get(qt, 0)
            if f:
                scores[i] += idf * f / (f + 1.2)
    return scores


def _norm_max(values: list[float]) -> list[float]:
    m = max(values, default=0.0)
    if m <= 0:
        return [0.0] * len(values)
    return [v / m for v in values]


def retrieve(document_ids: list[int] | None, query: str, k: int = 5) -> list[Context]:
    if not document_ids:
        return []
    embedder = get_embedder()
    store = get_vector_store()
    qv = embedder.embed([query])[0]

    candidates: list[tuple[int, dict]] = []
    for doc_id in document_ids:
        for hit in store.search(doc_id, qv, k=_CANDIDATES_PER_DOC):
            meta = hit.get("meta", {}) or {}
            hit = {**hit, "meta": {**meta, "document_id": doc_id}}
            candidates.append((doc_id, hit))

    if not candidates:
        return []

    lex = _bm25_scores(query, [c for _, c in candidates])
    cos = _norm_max([c["score"] for _, c in candidates])
    lexn = _norm_max(lex)

    scored = []
    for i, (doc_id, c) in enumerate(candidates):
        final = 0.45 * cos[i] + 0.55 * lexn[i]
        scored.append((final, doc_id, c))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        Context(
            text=c["text"],
            score=s,
            source=c.get("meta", {}).get("source", f"document {doc_id}"),
            meta=c.get("meta", {}),
        )
        for s, doc_id, c in scored[:k]
    ]


def all_contexts(document_ids: list[int] | None, limit: int = 60) -> list[Context]:
    """Full (evenly sampled) chunk set of the documents — used for
    generation tasks that should see the whole material, not just top-k."""
    if not document_ids:
        return []
    store = get_vector_store()
    out: list[Context] = []
    for doc_id in document_ids:
        for chunk in store.all_chunks(doc_id, limit=limit):
            meta = chunk.get("meta", {}) or {}
            out.append(
                Context(
                    text=chunk["text"],
                    score=0.0,
                    source=meta.get("source", f"document {doc_id}"),
                    meta={**meta, "document_id": doc_id},
                )
            )
    return out

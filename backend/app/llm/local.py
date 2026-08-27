"""Local (key-free) AI engine.

Deterministic, dependency-free heuristics so the whole platform is fully
functional without any external API key:

* summarization  -> frequency-ranked extractive sentences
* RAG answers    -> sentence-level relevance scoring over retrieved chunks
* MCQs           -> fact-sentence extraction; distractors are same-doc
                    sentences (easy/medium) or mutated copies (hard)
* flashcards     -> definition pattern mining + fill-in-the-blank
* study plans    -> topic-driven 5-day template
"""

import math
import random
import re
from collections import Counter
from typing import Any

from .base import Context, Flashcard, MCQ

STOPWORDS = set(
    """a an the and or but if then else when while of to in on at by for with about against
    between into through during before after above below from up down out off over under again
    further once here there all any both each few more most other some such no nor not only own
    same so than too very can will just should now is are was were be been being have has had
    do does did doing this that these those i you he she it we they what which who whom whose
    as s t don didn isn aren weren won wouldn per vs etc one two three also may might could""".split()
)

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-']*")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


# --- text helpers -------------------------------------------------------------
def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def is_stop(word: str) -> bool:
    return word in STOPWORDS or len(word) < 4


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    parts = _SENT_SPLIT.split(flat)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 25:
            out.append(p)
    return out


def key_terms(text: str, topn: int = 10) -> list[str]:
    counts = Counter(t for t in tokens(text) if not is_stop(t))
    return [w for w, _ in counts.most_common(topn)]


def _overlap_score(sentence: str, qtokens: set[str]) -> float:
    stoks = set(tokens(sentence))
    if not stoks:
        return 0.0
    return len(qtokens & stoks) / math.sqrt(len(stoks))


# --- provider -------------------------------------------------------------------
class LocalProvider:
    name = "local"

    # -- summarization -----------------------------------------------------
    def summarize(self, text: str, max_words: int = 180) -> str:
        sents = sentences(text)
        if not sents:
            return "No readable content was found in this document."
        freq = Counter(t for t in key_terms(text, 25))
        if not freq:
            freq = Counter(tokens(text))

        def score(s: str) -> float:
            toks = [t for t in tokens(s) if not is_stop(t)]
            if not toks:
                return 0.0
            return sum(freq.get(t, 0) for t in toks) / math.sqrt(len(toks))

        ranked = sorted(range(len(sents)), key=lambda i: score(sents[i]), reverse=True)
        budget = max(3, max_words // 14)
        chosen = sorted(ranked[: min(budget, len(sents))])
        return " ".join(sents[i] for i in chosen)

    # -- RAG Q&A ------------------------------------------------------------
    def answer(self, question: str, contexts: list[Context]) -> str:
        pool = [(s, c) for c in contexts for s in sentences(c.text)]
        if not pool:
            return (
                "I couldn't find any relevant content in your documents yet. "
                "Upload a document first, then ask me about it."
            )
        qtok = set(t for t in tokens(question) if not is_stop(t))
        max_ctx = max((c.score for c in contexts), default=1.0) or 1.0

        def rel(item):
            s, c = item
            base = _overlap_score(s, qtok) if qtok else 0.0
            return base + 0.25 * (c.score / max_ctx if max_ctx > 0 else 0.0)

        best = sorted(pool, key=rel, reverse=True)[:2]
        if qtok and _overlap_score(best[0][0], qtok) == 0:
            return (
                "I couldn't find a direct answer in your documents. Try rephrasing with "
                "keywords from the material, or upload the document that covers this topic."
            )
        sources = {c.source for _, c in best if c.source}
        scope = "your document" if len(sources) <= 1 else "your documents"
        body = " ".join(s for s, _ in best).strip()
        return f"Based on {scope}, here's what I found:\n\n{body}"

    # -- explanations ---------------------------------------------------------
    def explain(self, question: str, contexts: list[Context]) -> str:
        pool = [(s, c) for c in contexts for s in sentences(c.text)]
        if not pool:
            return (
                "I don't have enough context to explain that yet. Upload the document "
                "that covers this topic and I'll break it down for you."
            )
        qtok = set(t for t in tokens(question) if not is_stop(t))
        pool.sort(key=lambda sc: _overlap_score(sc[0], qtok) if qtok else sc[1].score, reverse=True)
        top = [s for s, _ in pool[:3]]
        terms = key_terms(" ".join(top), 3)
        lines = ["Let's break this down.\n"]
        lines += [f"• {s}" for s in top[:2]]
        if terms:
            lines.append(
                f"\nThe core idea connects {', '.join(terms)} — read those sentences again "
                "and notice how each concept builds on the previous one."
            )
        lines.append(
            "\nStudy tip: restate this concept in your own words, then check yourself against "
            "the document. Explaining it out loud (or to an imaginary classmate) exposes gaps "
            "much faster than re-reading."
        )
        return "\n".join(lines)

    # -- MCQ generation ---------------------------------------------------------
    def generate_mcqs(self, contexts: list[Context], count: int = 5, difficulty: str = "medium") -> list[MCQ]:
        rng = random.Random()
        all_sents = [(s, c) for c in contexts for s in sentences(c.text)]
        candidates = [s for s, _ in all_sents if 30 <= len(s) <= 175]
        if len(candidates) < 4:
            candidates = [s for s, _ in all_sents]
        if not candidates:
            return []
        all_terms = key_terms(" ".join(s for s, _ in all_sents), 15)

        # difficulty biases candidate sentence length (hard -> denser sentences)
        ordered = sorted(candidates, key=lambda s: len(s), reverse=(difficulty == "hard"))
        if difficulty == "easy":
            ordered = sorted(ordered, key=lambda s: len(s))

        mcqs: list[MCQ] = []
        used: set[str] = set()
        used_terms: set[str] = set()
        for s in rng.sample(ordered, len(ordered)):
            if len(mcqs) >= count:
                break
            if s in used:
                continue
            s_terms = key_terms(s, 3)
            term = next((t for t in s_terms if t not in used_terms), None)
            if term is None:
                continue
            others = [o for o in candidates if o != s]
            if len(others) < 3:
                continue

            if difficulty == "easy":
                q = "According to the material, which of the following statements is correct?"
                distractors = rng.sample(others, 3)
                expl = f"The document states: “{s}”"
            elif difficulty == "medium":
                q = f"What does the material say about “{term}”?"
                pool_d = [o for o in others if term not in o]
                if len(pool_d) < 3:
                    pool_d = others
                distractors = rng.sample(pool_d, 3)
                expl = f"Directly from the text: “{s}”"
            else:
                q = f"Which statement is most consistent with the section on “{term}”?"
                distractors: list[str] = []
                for _ in range(8):
                    m = self._mutate(s, all_terms, rng)
                    if m and m != s and m not in distractors:
                        distractors.append(m)
                    if len(distractors) == 3:
                        break
                if len(distractors) < 3:
                    fill = [o for o in others if o not in distractors]
                    distractors += rng.sample(fill, min(3 - len(distractors), len(fill)))
                expl = f"The document says: “{s}”. The other options alter or contradict the source text."

            if len(distractors) < 3:
                continue
            opts = [s, *distractors]
            order = list(range(4))
            rng.shuffle(order)
            options = [opts[i] for i in order]
            used.add(s)
            used_terms.add(term)
            mcqs.append(
                MCQ(
                    question=q,
                    options=options,
                    correct_index=order.index(0),
                    explanation=expl,
                    topic=term,
                    difficulty=difficulty,
                )
            )
        return mcqs[:count]

    @staticmethod
    def _mutate(sentence: str, all_terms: list[str], rng: random.Random) -> str | None:
        """Create a plausible-but-false variant of a fact sentence."""
        s = sentence
        m = re.search(r"\d+", s)
        if m and rng.random() < 0.5:
            num = int(m.group(0))
            alt = max(1, num + rng.choice([1, 2, 3, 4]))
            return s.replace(m.group(0), str(alt), 1)
        candidates = [t for t in all_terms if t in s]
        if candidates:
            t = rng.choice(candidates)
            alts = [x for x in all_terms if x != t and x not in s][:5]
            if alts:
                return s.replace(t, rng.choice(alts), 1)
        m2 = re.search(r"\b(is|are|was|were)\b", s)
        if m2:
            verb = m2.group(1)
            neg = "are not" if verb == "are" else "is not" if verb == "is" else "was not"
            return s[: m2.start()] + neg + s[m2.end() :]
        return None

    # -- flashcard generation ---------------------------------------------------
    def generate_flashcards(self, contexts: list[Context], count: int = 10, difficulty: str = "medium") -> list[Flashcard]:
        all_sents = [s for c in contexts for s in sentences(c.text)]
        if difficulty == "easy":
            all_sents.sort(key=len)
        elif difficulty == "hard":
            all_sents.sort(key=len, reverse=True)

        cards: list[Flashcard] = []
        seen: set[str] = set()

        def push(front: str, back: str):
            key = front.lower()
            if key in seen or len(front) < 8:
                return
            seen.add(key)
            cards.append(Flashcard(front=front, back=back))

        # 1) explicit "X is/are/... Y" definitions
        defn = re.compile(
            r"([A-Z][A-Za-z0-9 \-]{3,45}?)\s+"
            r"(is|are|refers to|mean|means|defined as|known as|consists of|includes|encompasses|represents)\s+"
            r"(.{8,240}?)(?:[.!?]|$)"
        )
        for s in all_sents:
            for m in defn.finditer(s):
                term, verb, rest = m.group(1).strip(), m.group(2), m.group(3).strip()
                if term.lower() in {"it", "this", "that", "these", "those"}:
                    continue
                push(f"What is {term}?", f"{term} {verb} {rest}.")
            if len(cards) >= count * 2:
                break

        # 2) fill-in-the-blank on key terms
        terms = key_terms(" ".join(all_sents), 20)
        for s in all_sents:
            if len(s) > 160:
                continue
            for t in terms[:12]:
                if t in s:
                    push("Fill in the blank: " + s.replace(t, "______", 1), f"{t} — {s}")
                    break
            if len(cards) >= count * 2:
                break

        rng = random.Random()
        # deterministic-ish mix: keep definitions first, shuffle the rest
        defs = [c for c in cards if c.front.startswith("What is")]
        rest = [c for c in cards if not c.front.startswith("What is")]
        rng.shuffle(rest)
        return (defs + rest)[:count]

    # -- study plans ---------------------------------------------------------------
    def generate_study_plan(self, profile: dict[str, Any]) -> dict:
        docs = profile.get("documents") or []
        scores = profile.get("recent_scores") or []
        avg = round(sum(scores) / len(scores)) if scores else None
        titles = [d.get("title", "material") for d in docs] or ["your material"]
        topics: list[str] = []
        for d in docs:
            topics.extend([t for t in d.get("topics", [])[:3] if t not in topics])
        topics = topics[:8] or ["core concepts"]
        n_docs = max(1, len(titles))

        days = [
            {
                "day": 1,
                "focus": f"Orientation: {titles[0]}",
                "tasks": [
                    f"Read the AI summary of {titles[0]} and underline the main ideas",
                    "Skim each section and write one sentence per section in your own words",
                    f"List the 3 things you still don't understand about {topics[0]}",
                ],
            },
            {
                "day": 2,
                "focus": "Deep dive into core concepts",
                "tasks": [
                    f"Study {topics[0]} in detail; make a short mind map",
                    f"Drill 10 flashcards covering {', '.join(topics[:2])}",
                    "Ask the AI tutor to explain anything that still feels fuzzy",
                ],
            },
            {
                "day": 3,
                "focus": "Active recall & practice",
                "tasks": [
                    f"Attempt a medium-difficulty quiz across {n_docs} document(s)",
                    "Review every question you missed, reading the explanation carefully",
                    "Re-explain each missed answer out loud without looking at notes",
                ],
            },
            {
                "day": 4,
                "focus": "Weak spots & spaced review",
                "tasks": [
                    f"Re-study {topics[-1]} and anything marked 'Again' in flashcards",
                    "Redo the flashcards you got wrong yesterday",
                    "Write a one-page cheat sheet from memory, then check it",
                ],
            },
            {
                "day": 5,
                "focus": "Mock exam & consolidation",
                "tasks": [
                    "Take a hard-difficulty quiz under time pressure",
                    f"Compare your score to your average ({avg}%)" if avg is not None else "Track your score trend in Analytics",
                    "Plan a short review pass the day before your exam",
                ],
            },
        ]
        goal = f"Master {n_docs} document(s) and finish with a confident quiz score"
        if avg is not None:
            goal += f" (current average: {avg}%)"
        return {
            "title": "5-day personalised study plan",
            "goal": goal,
            "total_days": 5,
            "days": days,
        }

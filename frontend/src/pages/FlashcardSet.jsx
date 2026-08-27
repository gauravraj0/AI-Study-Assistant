import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorNote, Spinner } from "../components/ui.jsx";

const RATES = [
  { quality: 0, label: "🔁 Again", cls: "rate-again" },
  { quality: 1, label: "👍 Good", cls: "rate-good" },
  { quality: 2, label: "⚡ Easy", cls: "rate-easy" },
];

export default function FlashcardSet() {
  const { id } = useParams();
  const [cards, setCards] = useState(null);
  const [error, setError] = useState("");
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [finished, setFinished] = useState(false);

  const load = useCallback(() => {
    api(`/flashcards/sets/${id}`)
      .then((c) => {
        setCards(c);
        setIdx(0);
        setFinished(false);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  const review = async (quality) => {
    const card = cards[idx];
    try {
      await api(`/flashcards/cards/${card.id}/review`, { method: "POST", body: { quality } });
      setCards((cs) => cs.map((c) => (c.id === card.id ? { ...c, times_seen: c.times_seen + 1 } : c)));
      setFlipped(false);
      if (idx < cards.length - 1) setIdx(idx + 1);
      else setFinished(true);
    } catch (e) {
      setError(e.message);
    }
  };

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!cards) return (
    <div className="page">
      <Spinner label="Loading cards…" />
    </div>
  );
  if (cards.length === 0)
    return (
      <div className="page">
        <ErrorNote error="This deck has no cards." />
      </div>
    );

  if (finished)
    return (
      <div className="page">
        <div className="page-head">
          <div>
            <h1>Deck complete 🎉</h1>
            <p className="page-sub">You reviewed {cards.length} cards. Intervals are now scheduled — come back tomorrow.</p>
          </div>
        </div>
        <div className="card">
          <Link className="btn primary" to="/flashcards">
            ← Back to decks
          </Link>
          <button className="btn" onClick={load}>
            Study again
          </button>
        </div>
      </div>
    );

  const card = cards[idx];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Study session</h1>
          <p className="page-sub">
            Card {idx + 1} of {cards.length} · seen {card.times_seen}×
          </p>
        </div>
        <Link className="btn ghost small" to="/flashcards">
          ← Decks
        </Link>
      </div>

      <div className="fc-area">
        <div className={`flashcard ${flipped ? "flipped" : ""}`} onClick={() => setFlipped(!flipped)}>
          <div className="fc-inner">
            <div className="fc-side fc-front">
              <div className="fc-kicker">Question — click to reveal</div>
              <div className="fc-text">{card.front}</div>
            </div>
            <div className="fc-side fc-back">
              <div className="fc-kicker">Answer</div>
              <div className="fc-text">{card.back}</div>
            </div>
          </div>
        </div>

        {flipped ? (
          <div className="fc-rates">
            {RATES.map((r) => (
              <button key={r.quality} className={`btn rate ${r.cls}`} onClick={() => review(r.quality)}>
                {r.label}
              </button>
            ))}
          </div>
        ) : (
          <button className="btn" onClick={() => setFlipped(true)}>
            Show answer
          </button>
        )}
      </div>
    </div>
  );
}

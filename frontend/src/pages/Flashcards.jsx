import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, fmtDate } from "../api";
import { Badge, Empty, ErrorNote, PageHead, ProgressBar, Spinner } from "../components/ui.jsx";

export default function Flashcards() {
  const [params] = useSearchParams();
  const [docs, setDocs] = useState([]);
  const [sets, setSets] = useState(null);
  const [docId, setDocId] = useState(params.get("doc") ? Number(params.get("doc")) : "");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api("/flashcards/sets").then(setSets).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    api("/documents").then((d) => setDocs(d.filter((x) => x.status === "ready"))).catch(() => {});
    load();
  }, [load]);

  const generate = async () => {
    if (!docId) return;
    setBusy(true);
    setError("");
    try {
      await api("/flashcards/generate", { method: "POST", body: { document_id: docId, difficulty, count } });
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <PageHead title="Flashcards" sub="Automatic flashcard decks with spaced-repetition review (Again / Good / Easy)." />

      <div className="card generator">
        <div className="gen-title">⚙️ Generate a new deck</div>
        <div className="gen-row">
          <label>
            Document
            <select value={docId} onChange={(e) => setDocId(Number(e.target.value))}>
              <option value="">Choose a document…</option>
              {docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Difficulty
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="easy">🟢 Easy</option>
              <option value="medium">🟡 Medium</option>
              <option value="hard">🔴 Hard</option>
            </select>
          </label>
          <label>
            Cards
            <input type="number" min={4} max={30} value={count} onChange={(e) => setCount(Number(e.target.value))} />
          </label>
          <button className="btn primary" onClick={generate} disabled={busy || !docId}>
            {busy ? "Generating…" : "🃏 Generate deck"}
          </button>
        </div>
        {docs.length === 0 && <div className="muted small-pad">Upload a document first to generate flashcards.</div>}
      </div>

      <ErrorNote error={error} onRetry={load} />
      {!sets ? (
        <Spinner label="Loading decks…" />
      ) : sets.length === 0 ? (
        <Empty icon="🃏" title="No flashcard decks yet" sub="Generate one above — cards are mined from definitions and key concepts." />
      ) : (
        <div className="quiz-list">
          {sets.map((s) => (
            <div key={s.id} className="card quiz-card">
              <div className="quiz-card-main">
                <div className="quiz-title">{s.title}</div>
                <div className="doc-row-meta">
                  {s.card_count} cards · {fmtDate(s.created_at)} {s.document_name ? `· ${s.document_name}` : ""}
                </div>
                <ProgressBar pct={(s.card_count ? (s.reviewed_count / s.card_count) * 100 : 0)} />
              </div>
              <div className="quiz-card-actions">
                <Badge tone="warn">{s.difficulty}</Badge>
                <Link className="btn small primary" to={`/flashcards/${s.id}`}>
                  ▶ Study
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

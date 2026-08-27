import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, fmtDate } from "../api";
import { Badge, Empty, ErrorNote, PageHead, Spinner } from "../components/ui.jsx";

export default function Quizzes() {
  const [params] = useSearchParams();
  const [docs, setDocs] = useState([]);
  const [quizzes, setQuizzes] = useState(null);
  const [docId, setDocId] = useState(params.get("doc") ? Number(params.get("doc")) : "");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [justCreated, setJustCreated] = useState(null);

  const load = useCallback(() => {
    api("/quizzes").then(setQuizzes).catch((e) => setError(e.message));
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
      const q = await api("/quizzes/generate", { method: "POST", body: { document_id: docId, difficulty, count } });
      load();
      navigateAfter(q.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // stay on the list and highlight the fresh quiz
  const navigateAfter = (id) => setJustCreated(id);

  return (
    <div className="page">
      <PageHead title="Quizzes" sub="Generate automatic MCQs from any document — pick a difficulty, take the quiz, and learn from the explanations." />

      <div className="card generator">
        <div className="gen-title">⚙️ Generate a new quiz</div>
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
              <option value="easy">🟢 Easy — direct recall</option>
              <option value="medium">🟡 Medium — comprehension</option>
              <option value="hard">🔴 Hard — tricky distractors</option>
            </select>
          </label>
          <label>
            Questions
            <input
              type="number"
              min={3}
              max={15}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </label>
          <button className="btn primary" onClick={generate} disabled={busy || !docId}>
            {busy ? "Generating…" : "🎲 Generate quiz"}
          </button>
        </div>
        {docs.length === 0 && <div className="muted small-pad">Upload a document first to generate quizzes.</div>}
      </div>

      <ErrorNote error={error} onRetry={load} />
      {!quizzes ? (
        <Spinner label="Loading quizzes…" />
      ) : quizzes.length === 0 ? (
        <Empty icon="📝" title="No quizzes yet" sub="Generate your first one above — it takes a few seconds." />
      ) : (
        <div className="quiz-list">
          {quizzes.map((q) => (
            <div key={q.id} className={`card quiz-card ${justCreated === q.id ? "just-created" : ""}`}>
              <div className="quiz-card-main">
                <div className="quiz-title">{q.title}</div>
                <div className="doc-row-meta">
                  {q.num_questions} questions · {fmtDate(q.created_at)}
                  {q.document_name ? ` · ${q.document_name}` : ""}
                </div>
              </div>
              <div className="quiz-card-actions">
                {q.submitted_at ? (
                  <>
                    <Badge tone={q.passed ? "good" : "bad"}>{q.score}%</Badge>
                    <Link className="btn small" to={`/quizzes/${q.id}`}>
                      Review answers
                    </Link>
                  </>
                ) : (
                  <>
                    <Badge tone="warn">{q.difficulty}</Badge>
                    <Link className="btn small primary" to={`/quizzes/take/${q.id}`}>
                      ▶ Take quiz
                    </Link>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

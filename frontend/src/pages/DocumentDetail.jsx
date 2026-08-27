import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, fmtDate } from "../api";
import { Badge, ErrorNote, Spinner } from "../components/ui.jsx";

export default function DocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api(`/documents/${id}`)
      .then(setDoc)
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  const regenerate = async () => {
    setBusy(true);
    setError("");
    try {
      setDoc(await api(`/documents/${id}/summarize`, { method: "POST", body: { max_words: 180 } }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!doc) return (
    <div className="page">
      <Spinner label="Loading document…" />
    </div>
  );

  return (
    <div className="page">
      <button className="btn ghost small" onClick={() => navigate("/documents")}>
        ← Back to documents
      </button>

      <div className="card doc-detail">
        <div className="doc-detail-head">
          <span className="doc-icon big">{doc.file_type === "pdf" ? "📄" : doc.file_type === "docx" ? "📃" : "📝"}</span>
          <div>
            <h1>{doc.original_name}</h1>
            <div className="doc-row-meta">
              {doc.num_pages} pages · {doc.num_chunks} chunks indexed · uploaded {fmtDate(doc.created_at)} · {doc.quiz_count} quizzes ·{" "}
              {doc.flashcard_count} flashcard decks
            </div>
          </div>
          <Badge tone={doc.status === "ready" ? "good" : "bad"}>{doc.status}</Badge>
        </div>

        <div className="doc-actions">
          <Link className="btn primary" to={`/chat?doc=${doc.id}`}>
            🤖 Chat about this document
          </Link>
          <Link className="btn" to={`/quizzes?doc=${doc.id}`}>
            📝 Generate quiz
          </Link>
          <Link className="btn" to={`/flashcards?doc=${doc.id}`}>
            🃏 Generate flashcards
          </Link>
          <button className="btn ghost" onClick={regenerate} disabled={busy}>
            {busy ? "Regenerating…" : "✨ Regenerate summary"}
          </button>
        </div>

        <h3 className="section-title">AI summary</h3>
        {doc.summary ? (
          <p className="doc-summary-full">{doc.summary}</p>
        ) : (
          <div className="muted">No summary available.</div>
        )}
        {doc.error && <div className="form-error">{doc.error}</div>}
      </div>
    </div>
  );
}

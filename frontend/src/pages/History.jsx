import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDateTime } from "../api";
import { Empty, ErrorNote, PageHead, Spinner } from "../components/ui.jsx";

const TYPE_META = {
  document_uploaded: { icon: "📚", label: "Document uploaded" },
  document_deleted: { icon: "🗑️", label: "Document deleted" },
  summary_generated: { icon: "✨", label: "Summary generated" },
  chat_question: { icon: "🤖", label: "Tutor question" },
  quiz_generated: { icon: "📝", label: "Quiz generated" },
  quiz_completed: { icon: "✅", label: "Quiz completed" },
  flashcards_generated: { icon: "🃏", label: "Flashcards generated" },
  study_plan_generated: { icon: "🗓️", label: "Study plan generated" },
};

export default function History() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  const load = useCallback(() => {
    api("/history?limit=100")
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!items) return (
    <div className="page">
      <Spinner label="Loading study history…" />
    </div>
  );

  const groups = ["all", "document_uploaded", "quiz_completed", "chat_question", "flashcards_generated", "study_plan_generated"];
  const shown = items.filter((a) => filter === "all" || a.type === filter);

  return (
    <div className="page">
      <PageHead title="Study History" sub="A full timeline of everything you've done — uploads, questions, quizzes, reviews.">
        <div className="filter-row">
          {groups.map((g) => (
            <button key={g} className={filter === g ? "chip active" : "chip"} onClick={() => setFilter(g)}>
              {g === "all" ? "All" : TYPE_META[g]?.label || g}
            </button>
          ))}
        </div>
      </PageHead>

      {shown.length === 0 ? (
        <Empty icon="🕘" title="Nothing here" sub="Your activity will be logged as you study." action={<Link className="btn primary" to="/documents">Upload material</Link>} />
      ) : (
        <div className="timeline">
          {shown.map((a) => {
            const meta = TYPE_META[a.type] || { icon: "•", label: a.type };
            return (
              <div key={a.id} className="tl-item">
                <div className="tl-dot">
                  <span>{meta.icon}</span>
                </div>
                <div className="card tl-card">
                  <div className="tl-head">
                    <span className="tl-type">{meta.label}</span>
                    <span className="tl-time">{fmtDateTime(a.created_at)}</span>
                  </div>
                  <div className="tl-detail">{a.detail}</div>
                  {a.document_id != null && (
                    <Link className="link small" to={`/documents/${a.document_id}`}>
                      Open document →
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

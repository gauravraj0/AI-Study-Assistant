import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api";
import { useAuth } from "../auth.jsx";
import { ACTIVITY_ICONS, Empty, ErrorNote, ProgressBar, Spinner, StatCard } from "../components/ui.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState([]);
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState("");

  const load = () => {
    setError("");
    Promise.all([api("/analytics/overview"), api("/documents"), api("/progress")])
      .then(([o, d, p]) => {
        setStats(o);
        setDocs(d);
        setProgress(p);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(load, []);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Welcome back, {user?.name?.split(" ")[0] || "student"} 👋</h1>
          <p className="page-sub">Here's how your studying is going.</p>
        </div>
        <div className="page-head-actions">
          <Link className="btn ghost" to="/quizzes">
            📝 Take a quiz
          </Link>
          <Link className="btn primary" to="/documents">
            ＋ Upload material
          </Link>
        </div>
      </div>

      <ErrorNote error={error} onRetry={load} />
      {!stats ? (
        <Spinner label="Loading your dashboard…" />
      ) : (
        <>
          <div className="stat-grid">
            <StatCard icon="📚" label="Documents" value={stats.documents} sub={`${stats.ready_documents} ready`} />
            <StatCard
              icon="📝"
              label="Quizzes completed"
              value={stats.submitted_quizzes}
              sub={`${stats.quizzes} generated · ${stats.pass_rate != null ? stats.pass_rate + "% pass rate" : "no results yet"}`}
            />
            <StatCard icon="🎯" label="Average score" value={stats.average_score != null ? `${stats.average_score}%` : "—"} accent="good" />
            <StatCard icon="🔥" label="Day streak" value={stats.streak_days} sub={`${stats.chat_messages} tutor messages`} accent="warn" />
            <StatCard icon="🃏" label="Flashcards reviewed" value={stats.flashcards_reviewed} sub={`${stats.flashcards_total} in your decks`} />
          </div>

          <div className="two-col">
            <section className="card">
              <div className="card-head">
                <h2>Your material</h2>
                <Link to="/documents" className="link">
                  View all
                </Link>
              </div>
              {docs.length === 0 ? (
                <Empty
                  icon="📚"
                  title="No documents yet"
                  sub="Upload a PDF, DOCX, TXT or Markdown file to start learning with AI."
                  action={
                    <Link className="btn primary" to="/documents">
                      Upload your first document
                    </Link>
                  }
                />
              ) : (
                <div className="doc-list">
                  {docs.slice(0, 5).map((d) => {
                    const p = progress.find((x) => x.document_id === d.id);
                    return (
                      <Link key={d.id} className="doc-row" to={`/documents/${d.id}`}>
                        <span className="doc-icon">
                          {d.file_type === "pdf" ? "📄" : d.file_type === "docx" ? "📃" : "📝"}
                        </span>
                        <span className="doc-row-main">
                          <span className="doc-row-name">{d.original_name}</span>
                          <span className="doc-row-meta">
                            {d.num_pages} pages · {d.num_chunks} chunks · {d.quiz_count} quizzes · {fmtDate(d.created_at)}
                          </span>
                          {p && (
                            <span className="doc-row-progress">
                              <ProgressBar pct={p.progress_pct} />
                              <span className="doc-row-pct">{Math.round(p.progress_pct)}%</span>
                            </span>
                          )}
                        </span>
                        <span className={`doc-status status-${d.status}`}>{d.status}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </section>

            <section className="card">
              <div className="card-head">
                <h2>Recent activity</h2>
                <Link to="/history" className="link">
                  Full history
                </Link>
              </div>
              {stats.recent_activity.length === 0 ? (
                <Empty icon="🕘" title="Nothing here yet" sub="Your study actions will show up here." />
              ) : (
                <ul className="activity-list">
                  {stats.recent_activity.map((a, i) => (
                    <li key={i}>
                      <span className="activity-icon">{ACTIVITY_ICONS[a.type] || "•"}</span>
                      <span className="activity-detail">{a.detail}</span>
                      <span className="activity-time">{fmtDate(a.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}

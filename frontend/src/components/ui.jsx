export const ACTIVITY_ICONS = {
  document_uploaded: "📚",
  document_deleted: "🗑️",
  chat_question: "🤖",
  quiz_generated: "📝",
  quiz_completed: "✅",
  flashcards_generated: "🃏",
  study_plan_generated: "🗓️",
  summary_generated: "✨",
};

export function Spinner({ label = "Working…" }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      {label && <div className="spinner-label">{label}</div>}
    </div>
  );
}

export function StatCard({ icon, label, value, sub, accent }) {
  return (
    <div className={`stat-card ${accent ? "accent-" + accent : ""}`}>
      <div className="stat-icon">{icon}</div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  );
}

export function Empty({ icon = "📭", title, sub, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {sub && <div className="empty-sub">{sub}</div>}
      {action}
    </div>
  );
}

export function Badge({ children, tone = "muted" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function ProgressBar({ pct }) {
  return (
    <div className="progress">
      <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
    </div>
  );
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-note">
      <span>⚠️ {error}</span>
      {onRetry && (
        <button className="btn ghost small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function PageHead({ title, sub, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p className="page-sub">{sub}</p>}
      </div>
      <div className="page-head-actions">{children}</div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { api, fmtDateTime } from "../api";
import { ErrorNote, PageHead, Spinner } from "../components/ui.jsx";

export default function Plans() {
  const [plans, setPlans] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api("/plans")
      .then(setPlans)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      await api("/plans/generate", { method: "POST" });
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <PageHead title="Study Plans" sub="Personalised, multi-day plans built from your documents and recent quiz performance.">
        <button className="btn primary" onClick={generate} disabled={busy}>
          {busy ? "Building your plan…" : "🗓️ Generate my study plan"}
        </button>
      </PageHead>

      <ErrorNote error={error} onRetry={load} />
      {!plans ? (
        <Spinner label="Loading plans…" />
      ) : plans.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">🗓️</div>
          <div className="empty-title">No plan yet</div>
          <div className="empty-sub">Generate one — it adapts to your material and weak topics.</div>
        </div>
      ) : (
        plans.map((p) => (
          <div key={p.id} className="card plan">
            <div className="plan-head">
              <div>
                <h2>{p.title}</h2>
                <div className="muted">{fmtDateTime(p.created_at)}</div>
              </div>
              <div className="plan-goal">🎯 {p.goal}</div>
            </div>
            <div className="plan-days">
              {p.days.map((d) => (
                <div key={d.day} className="plan-day">
                  <div className="plan-day-num">Day {d.day}</div>
                  <div>
                    <div className="plan-day-focus">{d.focus}</div>
                    <ul>
                      {d.tasks.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

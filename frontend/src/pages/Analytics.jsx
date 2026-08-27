import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, fmtDate } from "../api";
import { ACTIVITY_ICONS, Empty, ErrorNote, PageHead, Spinner, StatCard } from "../components/ui.jsx";

const TOOLTIP_STYLE = {
  backgroundColor: "#141b31",
  border: "1px solid rgba(255,255,255,.12)",
  borderRadius: 10,
  color: "#e8ecf8",
};

export default function Analytics() {
  const [stats, setStats] = useState(null);
  const [scores, setScores] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    Promise.all([api("/analytics/overview"), api("/analytics/scores"), api("/analytics/topics")])
      .then(([o, s, t]) => {
        setStats(o);
        setScores(s);
        setTopics(t);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!stats) return (
    <div className="page">
      <Spinner label="Crunching your numbers…" />
    </div>
  );

  return (
    <div className="page">
      <PageHead title="Performance Analytics" sub="How you're doing across quizzes, topics and review sessions." />

      <div className="stat-grid">
        <StatCard icon="🎯" label="Average quiz score" value={stats.average_score != null ? `${stats.average_score}%` : "—"} accent="good" />
        <StatCard icon="✅" label="Pass rate" value={stats.pass_rate != null ? `${stats.pass_rate}%` : "—"} />
        <StatCard icon="📝" label="Quizzes taken" value={stats.quizzes} />
        <StatCard icon="🃏" label="Cards reviewed" value={stats.flashcards_reviewed} sub={`of ${stats.flashcards_total} in decks`} />
        <StatCard icon="🔥" label="Day streak" value={stats.streak_days} accent="warn" />
      </div>

      <div className="two-col">
        <section className="card">
          <div className="card-head">
            <h2>Score trend</h2>
          </div>
          {scores.length === 0 ? (
            <Empty icon="📈" title="No quiz scores yet" sub="Complete a quiz to see your trend here." />
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={scores} margin={{ top: 8, right: 16, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="rgba(255,255,255,.06)" />
                  <XAxis dataKey="date" tick={{ fill: "#93a0c2", fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#93a0c2", fontSize: 12 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, "score"]} />
                  <Line type="monotone" dataKey="score" stroke="#22d3aa" strokeWidth={2.5} dot={{ fill: "#22d3aa", r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Accuracy by topic</h2>
          </div>
          {topics.length === 0 ? (
            <Empty icon="🧩" title="No topic data yet" sub="Submit a quiz and topic-level accuracy appears here." />
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={topics} margin={{ top: 8, right: 16, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="rgba(255,255,255,.06)" />
                  <XAxis dataKey="topic" tick={{ fill: "#93a0c2", fontSize: 11 }} interval={0} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#93a0c2", fontSize: 12 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, "accuracy"]} />
                  <Bar dataKey="accuracy" fill="#6c8cff" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Recent activity</h2>
        </div>
        <ul className="activity-list">
          {stats.recent_activity.map((a, i) => (
            <li key={i}>
              <span className="activity-icon">{ACTIVITY_ICONS[a.type] || "•"}</span>
              <span className="activity-detail">{a.detail}</span>
              <span className="activity-time">{fmtDate(a.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

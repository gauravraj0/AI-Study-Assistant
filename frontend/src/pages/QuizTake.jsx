import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorNote, Spinner } from "../components/ui.jsx";

export default function QuizTake() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api(`/quizzes/${id}`)
      .then((d) => {
        setData(d);
        setAnswers(new Array(d.questions.length).fill(null));
      })
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await api(`/quizzes/${id}/submit`, { method: "POST", body: { answers } });
      navigate(`/quizzes/${id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!data) return (
    <div className="page">
      <Spinner label="Loading quiz…" />
    </div>
  );

  const q = data.questions[idx];
  const answered = answers.filter((a) => a != null).length;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{data.quiz.title}</h1>
          <p className="page-sub">
            Question {idx + 1} of {data.questions.length} · {answered} answered
          </p>
        </div>
        <Link className="btn ghost small" to="/quizzes">
          ← Quit
        </Link>
      </div>

      <div className="quiz-take">
        <div className="quiz-steps">
          {data.questions.map((qq, i) => (
            <span key={qq.id} className={`step ${i === idx ? "active" : ""} ${answers[i] != null ? "done" : ""}`} />
          ))}
        </div>

        <div className="card quiz-question-card">
          {q.topic && <div className="quiz-topic">topic: {q.topic}</div>}
          <h2 className="quiz-question">{q.question}</h2>
          <div className="quiz-options">
            {q.options.map((opt, i) => (
              <button key={i} className={selected === i ? "quiz-option selected" : "quiz-option"} onClick={() => setSelected(i)}>
                <span className="quiz-option-letter">{String.fromCharCode(65 + i)}</span>
                {opt}
              </button>
            ))}
          </div>
        </div>

        <div className="quiz-nav">
          <button
            className="btn"
            disabled={idx === 0}
            onClick={() => {
              setIdx(idx - 1);
              setSelected(answers[idx - 1]);
            }}
          >
            ← Previous
          </button>
          <div className="quiz-nav-right">
            {selected != null && (
              <button
                className="btn"
                onClick={() => {
                  const next = [...answers];
                  next[idx] = selected;
                  setAnswers(next);
                  setSelected(null);
                  if (idx < data.questions.length - 1) setIdx(idx + 1);
                }}
              >
                Save answer
              </button>
            )}
            {idx === data.questions.length - 1 && (
              <button className="btn primary" disabled={busy || answered < data.questions.length} onClick={submit}>
                {busy ? "Scoring…" : "Submit quiz ✓"}
              </button>
            )}
          </div>
        </div>
        {answered < data.questions.length && idx === data.questions.length - 1 && (
          <div className="muted small-pad">Answer every question to submit.</div>
        )}
      </div>
    </div>
  );
}

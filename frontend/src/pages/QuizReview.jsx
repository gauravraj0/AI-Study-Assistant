import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fmtDateTime } from "../api";
import { Badge, ErrorNote, Spinner } from "../components/ui.jsx";

export default function QuizReview() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api(`/quizzes/${id}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  if (error) return (
    <div className="page">
      <ErrorNote error={error} onRetry={load} />
    </div>
  );
  if (!data) return (
    <div className="page">
      <Spinner label="Loading results…" />
    </div>
  );

  const { quiz, questions } = data;
  const correct = questions.filter((q) => q.your_answer === q.correct_index).length;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Quiz results</h1>
          <p className="page-sub">
            {quiz.title} · submitted {fmtDateTime(quiz.submitted_at)}
          </p>
        </div>
        <Link className="btn ghost small" to="/quizzes">
          ← All quizzes
        </Link>
      </div>

      <div className={`card score-banner ${quiz.passed ? "pass" : "fail"}`}>
        <div className="score-big">{quiz.score}%</div>
        <div>
          <div className="score-line">
            {correct}/{questions.length} correct · <Badge tone={quiz.passed ? "good" : "bad"}>{quiz.passed ? "passed" : "not passed"}</Badge>
          </div>
          <div className="muted">{quiz.passed ? "Solid work — now push for mastery with a harder quiz." : "Review the explanations below, then try again."}</div>
        </div>
      </div>

      <div className="review-list">
        {questions.map((q, i) => {
          const ok = q.your_answer === q.correct_index;
          return (
            <div key={q.id} className={`card review-card ${ok ? "ok" : "wrong"}`}>
              <div className="review-head">
                <span className="review-num">{i + 1}</span>
                <span className="review-q">{q.question}</span>
                <Badge tone={ok ? "good" : "bad"}>{ok ? "correct" : "incorrect"}</Badge>
              </div>
              <div className="review-options">
                {q.options.map((opt, oi) => (
                  <div
                    key={oi}
                    className={[
                      "review-opt",
                      oi === q.correct_index ? "is-correct" : "",
                      oi === q.your_answer && oi !== q.correct_index ? "is-wrong" : "",
                    ].join(" ")}
                  >
                    <span className="quiz-option-letter">{String.fromCharCode(65 + oi)}</span>
                    {opt}
                    {oi === q.correct_index && <span className="review-flag">✓ correct</span>}
                    {oi === q.your_answer && oi !== q.correct_index && <span className="review-flag bad">your answer</span>}
                  </div>
                ))}
              </div>
              <div className="review-expl">
                <b>Explanation:</b> {q.explanation}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

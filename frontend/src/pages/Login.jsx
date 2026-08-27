import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("demo@study.ai");
  const [password, setPassword] = useState("demo1234");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(name || "Student", email, password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-logo">🎓</span>
          <h1>AI Study Assistant</h1>
          <p>Upload your material. Chat with your tutor. Quiz yourself. Track your progress.</p>
        </div>
        <div className="tabs">
          <button className={mode === "login" ? "tab active" : "tab"} onClick={() => setMode("login")}>
            Sign in
          </button>
          <button className={mode === "register" ? "tab active" : "tab"} onClick={() => setMode("register")}>
            Create account
          </button>
        </div>
        <form onSubmit={submit}>
          {mode === "register" && (
            <label>
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Lovelace" required />
            </label>
          )}
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@school.edu" required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="min 6 characters"
              minLength={6}
              required
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="btn primary block" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <div className="login-hint">
          Demo account: <b>demo@study.ai</b> / <b>demo1234</b> — pre-loaded with two study documents.
        </div>
      </div>
    </div>
  );
}

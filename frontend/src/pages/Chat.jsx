import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, fmtDateTime } from "../api";
import { ErrorNote, Spinner } from "../components/ui.jsx";
import { speak, stopSpeaking, useVoice } from "../hooks.js";

export default function Chat() {
  const [params, setParams] = useSearchParams();
  const docId = params.get("doc") ? Number(params.get("doc")) : null;

  const [docs, setDocs] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [current, setCurrent] = useState(null); // session id
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("ask");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const voice = useVoice((t) => {
    setInput(t);
  });

  const loadSessions = useCallback(() => {
    api("/chat/sessions").then(setSessions).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    api("/documents").then(setDocs).catch(() => {});
    loadSessions();
  }, [loadSessions]);

  const openSession = (id) => {
    if (id == null) {
      setCurrent(null);
      setMessages([]);
      return;
    }
    setCurrent(id);
    setMessages([]);
    api(`/chat/sessions/${id}`)
      .then((s) => setMessages(s.messages))
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setError("");
    setBusy(true);
    stopSpeaking();
    try {
      let sid = current;
      if (sid == null) {
        const s = await api("/chat/sessions", { method: "POST", body: { document_id: docId } });
        sid = s.id;
        setCurrent(sid);
        loadSessions();
      }
      const optimisticId = Date.now();
      setMessages((m) => [...m, { id: optimisticId, role: "user", content, mode }]);
      setInput("");
      try {
        const msg = await api(`/chat/sessions/${sid}/messages`, { method: "POST", body: { content, mode } });
        setMessages((m) => [...m, msg]);
      } catch (e) {
        setMessages((m) => m.filter((x) => x.id !== optimisticId));
        throw e;
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const removeSession = async (id) => {
    if (!confirm("Delete this conversation?")) return;
    await api(`/chat/sessions/${id}`, { method: "DELETE" }).catch((e) => setError(e.message));
    if (current === id) {
      setCurrent(null);
      setMessages([]);
    }
    loadSessions();
  };

  const scopeDoc = docs.find((d) => d.id === docId);

  return (
    <div className="chat-page">
      <aside className="chat-sessions">
        <div className="chat-sessions-head">
          <h2>Conversations</h2>
          <button className="btn small primary" onClick={() => openSession(null)}>
            ＋ New
          </button>
        </div>
        {docId != null && (
          <div className="chat-scope">
            {scopeDoc ? scopeDoc.original_name : `Document ${docId}`}
            <button className="chat-scope-clear" title="Chat across all documents" onClick={() => setParams({})}>
              ✕
            </button>
          </div>
        )}
        <div className="chat-sessions-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={current === s.id ? "chat-session active" : "chat-session"}
              onClick={() => openSession(s.id)}
            >
              <div className="chat-session-title">{s.title}</div>
              <div className="chat-session-meta">
                {s.message_count} messages
                <button
                  className="chat-session-del"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSession(s.id);
                  }}
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
          {sessions.length === 0 && <div className="muted pad">No conversations yet.</div>}
        </div>
      </aside>

      <section className="chat-main">
        <div className="chat-msgs">
          {messages.length === 0 && (
            <div className="chat-empty">
              <div className="chat-empty-icon">🤖</div>
              <h3>Ask me anything about your material</h3>
              <p>
                {docId != null
                  ? `I'm reading "${scopeDoc?.original_name || "the selected document"}" and can answer questions, explain concepts, and generate practice.`
                  : "I search across all your uploaded documents (RAG) and answer with the most relevant passages."}
              </p>
              <div className="chat-suggestions">
                <button onClick={() => send("Summarize the key ideas in a few bullet points")}>✨ Key ideas</button>
                <button onClick={() => send("Explain the hardest concept in simple words")}>🧠 Explain a concept</button>
                <button onClick={() => send("What should I focus on studying first?")}>🎯 Study priorities</button>
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={m.role === "user" ? "msg user" : "msg ai"}>
              <div className="msg-avatar">{m.role === "user" ? "🧑" : "🤖"}</div>
              <div className="msg-bubble">
                <div className="msg-text">{m.content}</div>
                <div className="msg-foot">
                  <span>{fmtDateTime(m.created_at)}</span>
                  {m.mode === "explain" && <span className="msg-mode">explain</span>}
                  {m.role === "ai" && (
                    <span className="msg-actions">
                      <button title="Read aloud" onClick={() => speak(m.content)}>
                        🔊
                      </button>
                      <button
                        title="Ask for an explanation of this"
                        onClick={() => {
                          setMode("explain");
                          send(`Explain this: ${m.content.slice(0, 120)}`);
                        }}
                      >
                        💡
                      </button>
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {busy && (
            <div className="msg ai">
              <div className="msg-avatar">🤖</div>
              <div className="msg-bubble">
                <Spinner label="Thinking…" />
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {error && <ErrorNote error={error} />}

        <div className="chat-input">
          <div className="chat-input-modes">
            <button className={mode === "ask" ? "chip active" : "chip"} onClick={() => setMode("ask")}>
              ❓ Ask
            </button>
            <button className={mode === "explain" ? "chip active" : "chip"} onClick={() => setMode("explain")}>
              💡 Explain
            </button>
            {voice.supported ? (
              <span className="chip muted-chip">{voice.listening ? "🎤 listening…" : "🎤 voice questions ready"}</span>
            ) : (
              <span className="chip muted-chip">🎤 voice needs Chrome/Edge</span>
            )}
          </div>
          <div className="chat-input-row">
            {voice.supported && (
              <button
                className={voice.listening ? "voice-btn listening" : "voice-btn"}
                title={voice.listening ? "Stop listening" : "Ask by voice"}
                onClick={() => (voice.listening ? voice.stop() : voice.start())}
              >
                🎤
              </button>
            )}
            <textarea
              rows={2}
              placeholder={voice.listening ? "Listening… speak your question" : "Type or dictate a question…"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <button className="btn primary" onClick={() => send()} disabled={busy || !input.trim()}>
              Send ➤
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

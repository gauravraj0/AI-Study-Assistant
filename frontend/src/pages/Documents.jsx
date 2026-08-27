import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api";
import { Badge, Empty, ErrorNote, PageHead, Spinner } from "../components/ui.jsx";

export default function Documents() {
  const [docs, setDocs] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const fileRef = useRef(null);
  const [drag, setDrag] = useState(false);

  const load = useCallback(() => {
    api("/documents")
      .then(setDocs)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const upload = async (file) => {
    if (!file) return;
    setUploading(file.name);
    setError("");
    setNotice("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const doc = await api("/documents", { method: "POST", body: fd });
      setNotice(`“${doc.original_name}” processed — ${doc.num_chunks} chunks indexed, summary ready.`);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const remove = async (id) => {
    if (!confirm("Delete this document? Generated quizzes keep their results, but the document itself is removed.")) return;
    try {
      await api(`/documents/${id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <PageHead title="Documents" sub="Upload study material — it gets chunked, embedded, summarized and made available to the AI tutor." />

      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          upload(e.dataTransfer.files?.[0]);
        }}
      >
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md,.csv,.json" hidden onChange={(e) => upload(e.target.files?.[0])} />
        <div className="dropzone-icon">{busy ? "⏳" : "📤"}</div>
        <div className="dropzone-title">{uploading ? `Processing ${uploading}…` : "Drag & drop a file here"}</div>
        <div className="dropzone-sub">PDF, DOCX, TXT, MD, CSV or JSON — up to 25 MB</div>
        <button className="btn primary" onClick={() => fileRef.current?.click()} disabled={busy}>
          Choose file
        </button>
      </div>

      <ErrorNote error={error} onRetry={load} />
      {notice && <div className="notice">✅ {notice}</div>}

      {!docs ? (
        <Spinner label="Loading documents…" />
      ) : docs.length === 0 ? (
        <Empty icon="📚" title="No documents yet" sub="Your uploads will appear here with their AI summaries." />
      ) : (
        <div className="doc-grid">
          {docs.map((d) => (
            <div key={d.id} className="card doc-card">
              <div className="doc-card-top">
                <span className="doc-icon big">{d.file_type === "pdf" ? "📄" : d.file_type === "docx" ? "📃" : "📝"}</span>
                <div className="doc-card-name">
                  <Link to={`/documents/${d.id}`} className="link-strong">
                    {d.original_name}
                  </Link>
                  <div className="doc-row-meta">
                    {d.num_pages} pages · {d.num_chunks} chunks · {fmtDate(d.created_at)}
                  </div>
                </div>
                <Badge tone={d.status === "ready" ? "good" : d.status === "error" ? "bad" : "warn"}>{d.status}</Badge>
              </div>
              {d.summary && <p className="doc-summary">{d.summary.slice(0, 220)}{d.summary.length > 220 ? "…" : ""}</p>}
              <div className="doc-card-actions">
                <Link className="btn small" to={`/documents/${d.id}`}>
                  Open
                </Link>
                <Link className="btn small ghost" to={`/chat?doc=${d.id}`}>
                  🤖 Ask tutor
                </Link>
                <button className="btn small danger ghost" onClick={() => remove(d.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

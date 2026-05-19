import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchWorkspaces, ragQuery, reindexWorkspace } from "../api/ai";
import AppSidebar from "../components/AppSidebar";
import { AuthContext } from "../context/AuthContext";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

import "./Dashboard.css";
import "./AIAssistant.css";

const EXAMPLE_QUESTIONS = [
  "Why do we use JWT for login?",
  "What tasks do we have for authentication?",
  "Any comments about refresh tokens?",
];

const DOC_TYPE_LABELS = {
  task: "Task",
  comment: "Comment",
  project: "Project",
  activity: "Activity",
};

function docTypeLabel(type) {
  return DOC_TYPE_LABELS[type] || type;
}

function formatScore(score) {
  if (score == null) return null;
  return `${Math.round(Number(score) * 100)}% match`;
}

function AIAssistant() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const chatEndRef = useRef(null);
  const chatAbortRef = useRef(null);

  const [workspaces, setWorkspaces] = useState([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspacesLoading, setWorkspacesLoading] = useState(true);

  const [input, setInput] = useState("");
  const [chatTurns, setChatTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setWorkspacesLoading(true);
      try {
        const list = await fetchWorkspaces();
        if (cancelled) return;
        setWorkspaces(list);
        if (list.length > 0) setWorkspaceId(String(list[0].id));
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || "Could not load workspace.");
        }
      } finally {
        if (!cancelled) setWorkspacesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatTurns, loading]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
      chatAbortRef.current?.abort();
    };
  }, []);

  const wsId = workspaceId ? Number(workspaceId) : null;
  const selectedWorkspace = workspaces.find((w) => String(w.id) === workspaceId);
  const workspaceLabel = formatWorkspaceLabel(selectedWorkspace);

  const stopGeneration = useCallback(() => {
    chatAbortRef.current?.abort();
  }, []);

  const isAbortError = (err) =>
    err?.code === "ERR_CANCELED" ||
    err?.name === "CanceledError" ||
    err?.message === "canceled";

  const runChat = useCallback(
    async (text) => {
      if (!wsId || !text.trim() || loading) return;
      const q = text.trim();
      setInput("");
      setError("");

      chatAbortRef.current?.abort();
      const controller = new AbortController();
      chatAbortRef.current = controller;

      setLoading(true);
      setChatTurns((prev) => [...prev, { role: "user", text: q }]);

      try {
        const data = await ragQuery({
          workspaceId: wsId,
          question: q,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setChatTurns((prev) => [
          ...prev,
          {
            role: "assistant",
            text: data.answer,
            sources: data.sources || [],
          },
        ]);
      } catch (err) {
        if (isAbortError(err)) return;
        setError(
          err.response?.data?.detail ||
            "No response received. Check that the backend and GROQ_API_KEY are configured."
        );
      } finally {
        if (chatAbortRef.current === controller) {
          chatAbortRef.current = null;
        }
        setLoading(false);
      }
    },
    [wsId, loading]
  );

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (loading) {
      stopGeneration();
      return;
    }
    runChat(input);
  };

  const handleExample = (text) => runChat(text);

  const handleReindex = async () => {
    if (!wsId) return;
    setReindexing(true);
    setError("");
    try {
      await reindexWorkspace(wsId);
      setShowSettings(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Update failed.");
    } finally {
      setReindexing(false);
    }
  };

  const clearChat = () => {
    stopGeneration();
    setChatTurns([]);
    setError("");
  };

  const isEmpty = chatTurns.length === 0;
  const hasWorkspace = Boolean(wsId);

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main">
        <header className="ai-topbar">
          <h2 className="ai-heading">Ask about your project</h2>
          <div className="ai-topbar-actions">
            <select
              className="ai-select ai-select--compact"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              disabled={workspacesLoading}
              aria-label="Select workspace"
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {formatWorkspaceLabel(ws)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="ai-icon-btn"
              onClick={() => setShowSettings((v) => !v)}
              title="Settings"
              aria-expanded={showSettings}
            >
              ⚙
            </button>
          </div>
        </header>

        {showSettings ? (
          <div className="ai-settings">
            <p>
              <strong>Project memory</strong> — refresh when you add new tasks so the AI can find
              them.
            </p>
            <button
              type="button"
              className="ai-btn ai-btn--secondary"
              onClick={handleReindex}
              disabled={reindexing || !wsId}
            >
              {reindexing ? "Updating…" : "Refresh memory"}
            </button>
          </div>
        ) : null}

        {error ? (
          <div className="ai-error" role="alert">
            {error}
            <button type="button" className="ai-error-dismiss" onClick={() => setError("")}>
              ✕
            </button>
          </div>
        ) : null}

        {!workspacesLoading && !hasWorkspace ? (
          <div className="ai-no-workspace" role="alert">
            <strong>No workspace found.</strong>
            <p>
              Run in the backend folder:{" "}
              <code>python manage.py bootstrap_workspace --email=your@email.com</code>
              , then refresh.
            </p>
          </div>
        ) : null}

        <div className="ai-chat-area" aria-live="polite">
          {isEmpty && !loading && hasWorkspace ? (
            <div className="ai-welcome">
              <div className="ai-welcome-icon" aria-hidden>
                ✨
              </div>
              <h3>Hello{user?.email ? `, ${user.email.split("@")[0]}` : ""}!</h3>
              <p>
                You&apos;re working in <strong>{workspaceLabel}</strong>. Pick a question below or
                type your own.
              </p>
              <div className="ai-examples">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="ai-example-chip"
                    onClick={() => handleExample(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {chatTurns.map((turn, i) => (
            <div key={i} className={`ai-bubble ai-bubble--${turn.role}`}>
              <span className="ai-bubble-avatar">{turn.role === "user" ? "You" : "AI"}</span>
              <div className="ai-bubble-body">
                <p className="ai-bubble-text">{turn.text}</p>
                {turn.sources?.length > 0 ? (
                  <div className="ai-source-cards">
                    <span className="ai-source-label">Found in project:</span>
                    {turn.sources.slice(0, 4).map((s, j) => (
                      <div key={j} className="ai-source-card">
                        <span className="ai-source-type">{docTypeLabel(s.doc_type)}</span>
                        <strong>{s.title}</strong>
                        {formatScore(s.score) ? (
                          <span className="ai-source-score">{formatScore(s.score)}</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}

          {loading ? (
            <div className="ai-bubble ai-bubble--assistant ai-bubble--loading">
              <span className="ai-bubble-avatar">AI</span>
              <div className="ai-bubble-body">
                <span className="ai-typing">
                  <span />
                  <span />
                  <span />
                </span>
                <p className="ai-loading-text">Reading your tasks and comments…</p>
              </div>
            </div>
          ) : null}

          <div ref={chatEndRef} />
        </div>

        <footer className="ai-footer">
          <form className="ai-composer" onSubmit={handleSubmit}>
            <input
              className="ai-composer-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                loading ? "Generating… click Stop to cancel" : "Ask something about the project…"
              }
              disabled={!hasWorkspace}
            />
            <button
              type="submit"
              className={`ai-btn ai-btn--send${loading ? " ai-btn--stop" : ""}`}
              disabled={!hasWorkspace || (!loading && !input.trim())}
              aria-label={loading ? "Stop generating" : "Send"}
              title={loading ? "Stop" : "Send"}
            >
              {loading ? (
                <span className="ai-stop-icon" aria-hidden>
                  ■
                </span>
              ) : (
                "→"
              )}
            </button>
          </form>
          {!isEmpty ? (
            <button type="button" className="ai-clear-link" onClick={clearChat}>
              Clear chat
            </button>
          ) : null}
        </footer>
      </main>
    </div>
  );
}

export default AIAssistant;

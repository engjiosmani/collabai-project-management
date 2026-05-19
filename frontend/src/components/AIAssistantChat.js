import { forwardRef, useImperativeHandle } from "react";

import {
  EXAMPLE_QUESTIONS,
  docTypeLabel,
  formatScore,
  useAIAssistantChat,
} from "../hooks/useAIAssistantChat";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

import "../pages/AIAssistant.css";

const AIAssistantChat = forwardRef(function AIAssistantChat(
  { variant = "page", showWorkspaceSelect = true, onClearChat },
  ref
) {
  const chat = useAIAssistantChat();
  const {
    chatEndRef,
    workspaces,
    workspaceId,
    setWorkspaceId,
    workspacesLoading,
    input,
    setInput,
    chatTurns,
    loading,
    reindexing,
    showSettings,
    setShowSettings,
    error,
    setError,
    workspaceLabel,
    handleSubmit,
    handleExample,
    handleReindex,
    clearChat,
    abortOnUnmount,
    isEmpty,
    hasWorkspace,
    displayName,
  } = chat;

  useImperativeHandle(ref, () => ({ clearChat, abortOnUnmount }), [clearChat, abortOnUnmount]);

  const handleClear = () => {
    clearChat();
    onClearChat?.();
  };

  const rootClass =
    variant === "widget" ? "ai-chat ai-chat--widget" : "ai-chat ai-chat--page";

  return (
    <div className={rootClass}>
      {variant === "page" && showWorkspaceSelect ? (
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
      ) : null}

      {variant === "widget" && showWorkspaceSelect ? (
        <div className="ai-widget-workspace">
          <select
            className="ai-select ai-select--compact ai-select--widget"
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
            className="ai-icon-btn ai-icon-btn--widget"
            onClick={() => setShowSettings((v) => !v)}
            title="Settings"
            aria-expanded={showSettings}
          >
            ⚙
          </button>
        </div>
      ) : null}

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
            disabled={reindexing || !hasWorkspace}
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
            {variant === "page" ? (
              <div className="ai-welcome-icon" aria-hidden>
                ✨
              </div>
            ) : null}
            <h3>Hello{displayName ? `, ${displayName}` : ""}!</h3>
            <p>
              You&apos;re working in <strong>{workspaceLabel}</strong>.
              {variant === "page"
                ? " Pick a question below or type your own."
                : " How can I assist you today?"}
            </p>
            {variant === "page" ? (
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
            ) : null}
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
                <p className="ai-loading-text">
                  Reading your project context… First reply may take up to a minute.
                </p>
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
              variant === "widget"
                ? loading
                  ? "Generating…"
                  : "Write a message…"
                : loading
                  ? "Generating… click Stop to cancel"
                  : "Ask something about the project…"
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
        {!isEmpty && variant === "page" ? (
          <button type="button" className="ai-clear-link" onClick={handleClear}>
            Clear chat
          </button>
        ) : null}
      </footer>
    </div>
  );
});

export default AIAssistantChat;

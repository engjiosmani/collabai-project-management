import { forwardRef, useImperativeHandle } from "react";

import { useChatBot } from "../hooks/useChatBot";
import "../pages/AIAssistant.css";

const ChatBotPanel = forwardRef(function ChatBotPanel(_props, ref) {
  const {
    chatEndRef,
    input,
    setInput,
    turns,
    loading,
    error,
    setError,
    displayName,
    clearChat,
    abortOnUnmount,
    handleSubmit,
    isEmpty,
  } = useChatBot();

  useImperativeHandle(ref, () => ({ clearChat, abortOnUnmount }), [clearChat, abortOnUnmount]);

  return (
    <div className="ai-chat ai-chat--widget ai-chatbot">
      {error ? (
        <div className="ai-error" role="alert">
          {error}
          <button type="button" className="ai-error-dismiss" onClick={() => setError("")}>
            ✕
          </button>
        </div>
      ) : null}

      <div className="ai-chat-area" aria-live="polite">
        {isEmpty && !loading ? (
          <div className="ai-welcome">
            <h3>Hello{displayName ? `, ${displayName}` : ""}!</h3>
            <p>
              I&apos;m your general chatbot — ask anything. For questions about your project
              tasks and docs, use the{" "}
              <strong>AI Assistant</strong> page (RAG).
            </p>
          </div>
        ) : null}

        {turns.map((turn, i) => (
          <div key={i} className={`ai-bubble ai-bubble--${turn.role}`}>
            <span className="ai-bubble-avatar">{turn.role === "user" ? "You" : "Bot"}</span>
            <div className="ai-bubble-body">
              <p className="ai-bubble-text">{turn.text}</p>
            </div>
          </div>
        ))}

        {loading ? (
          <div className="ai-bubble ai-bubble--assistant ai-bubble--loading">
            <span className="ai-bubble-avatar">Bot</span>
            <div className="ai-bubble-body">
              <span className="ai-typing">
                <span />
                <span />
                <span />
              </span>
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
            placeholder={loading ? "Generating…" : "Write a message…"}
          />
          <button
            type="submit"
            className={`ai-btn ai-btn--send${loading ? " ai-btn--stop" : ""}`}
            disabled={!loading && !input.trim()}
            aria-label={loading ? "Stop" : "Send"}
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
      </footer>
    </div>
  );
});

export default ChatBotPanel;

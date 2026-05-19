import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useLocation } from "react-router-dom";

import AIAssistantChat from "./AIAssistantChat";
import { useDraggablePosition } from "../hooks/useDraggablePosition";

import "./FloatingAIAssistant.css";

const POS_KEY = "collabai-ai-widget-pos";
const HINT_KEY = "collabai-ai-widget-hint-dismissed";

function FloatingAIAssistant() {
  const { pathname } = useLocation();
  const chatRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [hintDismissed, setHintDismissed] = useState(() => {
    try {
      return localStorage.getItem(HINT_KEY) === "1";
    } catch {
      return false;
    }
  });

  const drag = useDraggablePosition(POS_KEY);
  const dragEndedRef = useRef(false);

  const hideWidget =
    pathname === "/ai" || pathname.startsWith("/ai/team-pulse");

  useEffect(() => {
    if (!open) return undefined;
    const chat = chatRef.current;
    return () => chat?.abortOnUnmount?.();
  }, [open]);

  if (hideWidget) return null;

  const handleFabPointerDown = (e) => {
    dragEndedRef.current = false;
    drag.onPointerDown(e);
  };

  const handleFabPointerMove = (e) => {
    drag.onPointerMove(e);
  };

  const handleFabPointerUp = (e) => {
    const wasDrag = drag.onPointerUp(e);
    dragEndedRef.current = wasDrag;
    if (!wasDrag) {
      setOpen((v) => !v);
      if (!hintDismissed) {
        setHintDismissed(true);
        try {
          localStorage.setItem(HINT_KEY, "1");
        } catch {
          /* ignore */
        }
      }
    }
  };

  const handleHeaderPointerDown = (e) => {
    if (e.target.closest("button, a")) return;
    dragEndedRef.current = false;
    drag.onPointerDown(e);
  };

  const handleHeaderPointerMove = (e) => {
    drag.onPointerMove(e);
  };

  const handleHeaderPointerUp = (e) => {
    drag.onPointerUp(e);
  };

  const dismissHint = () => {
    setHintDismissed(true);
    try {
      localStorage.setItem(HINT_KEY, "1");
    } catch {
      /* ignore */
    }
  };

  const widget = (
    <div
      className="ai-float-root"
      style={{ left: drag.position.x, top: drag.position.y }}
      role="presentation"
    >
      {open ? (
        <section className="ai-float-panel" aria-label="CollabAI Assistant chat">
          <header
            className="ai-float-header"
            onPointerDown={handleHeaderPointerDown}
            onPointerMove={handleHeaderPointerMove}
            onPointerUp={handleHeaderPointerUp}
          >
            <div className="ai-float-header-brand">
              <span className="ai-float-logo" aria-hidden>
                C
              </span>
              <div>
                <strong>CollabAI Assistant</strong>
                <span className="ai-float-status">Online</span>
              </div>
            </div>
            <div className="ai-float-header-actions">
              <button
                type="button"
                className="ai-float-icon-btn"
                title="Clear chat"
                aria-label="Clear chat"
                onClick={() => chatRef.current?.clearChat?.()}
              >
                🧹
              </button>
              <Link to="/ai" className="ai-float-icon-btn" title="Open full page" aria-label="Open full page">
                ↗
              </Link>
              <button
                type="button"
                className="ai-float-icon-btn ai-float-icon-btn--close"
                aria-label="Close assistant"
                onClick={() => setOpen(false)}
              >
                ✕
              </button>
            </div>
          </header>
          <AIAssistantChat ref={chatRef} variant="widget" showWorkspaceSelect />
        </section>
      ) : null}

      {!open && !hintDismissed ? (
        <button
          type="button"
          className="ai-float-hint"
          onClick={dismissHint}
          aria-label="Dismiss hint"
        >
          Talk to CollabAI Assistant here
        </button>
      ) : null}

      <button
        type="button"
        className={`ai-float-fab${open ? " ai-float-fab--open" : ""}`}
        aria-label={open ? "Close CollabAI Assistant" : "Open CollabAI Assistant"}
        aria-expanded={open}
        onPointerDown={open ? undefined : handleFabPointerDown}
        onPointerMove={open ? undefined : handleFabPointerMove}
        onPointerUp={open ? () => setOpen(false) : handleFabPointerUp}
      >
        {open ? (
          <span className="ai-float-fab-close" aria-hidden>
            ✕
          </span>
        ) : (
          <span className="ai-float-fab-logo" aria-hidden>
            C
          </span>
        )}
        {!open ? <span className="ai-float-online" aria-hidden /> : null}
      </button>
    </div>
  );

  return createPortal(widget, document.body);
}

export default FloatingAIAssistant;

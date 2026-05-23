import { useEffect, useRef, useState } from "react";

export default function GlobalApiToast() {
  const [toast, setToast] = useState({ message: "", tone: "error" });
  const timeoutRef = useRef(null);

  useEffect(() => {
    const showToast = (message, tone = "error") => {
      setToast({ message, tone });

      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = window.setTimeout(() => {
        setToast({ message: "", tone: "error" });
      }, 5000);
    };

    const handleApiError = (event) => {
      const nextMessage = event.detail?.message;
      if (!nextMessage) return;

      event.preventDefault();
      showToast(nextMessage, "error");
    };

    const handleAppToast = (event) => {
      const nextMessage = event.detail?.message;
      if (!nextMessage) return;
      showToast(nextMessage, event.detail?.tone || "success");
    };

    window.addEventListener("api:friendly-error", handleApiError);
    window.addEventListener("app:toast", handleAppToast);

    return () => {
      window.removeEventListener("api:friendly-error", handleApiError);
      window.removeEventListener("app:toast", handleAppToast);
      window.clearTimeout(timeoutRef.current);
    };
  }, []);

  if (!toast.message) return null;

  return (
    <div
      className={`global-api-toast global-api-toast--${toast.tone}`}
      role="alert"
      aria-live="assertive"
    >
      <span>{toast.message}</span>
      <button
        type="button"
        className="global-api-toast__close"
        onClick={() => setToast({ message: "", tone: "error" })}
        aria-label="Dismiss notification"
      >
        x
      </button>
    </div>
  );
}

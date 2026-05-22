import { useEffect, useRef, useState } from "react";

export default function GlobalApiToast() {
  const [message, setMessage] = useState("");
  const timeoutRef = useRef(null);

  useEffect(() => {
    const handleApiError = (event) => {
      const nextMessage = event.detail?.message;
      if (!nextMessage) return;

      event.preventDefault();
      setMessage(nextMessage);

      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = window.setTimeout(() => {
        setMessage("");
      }, 5000);
    };

    window.addEventListener("api:friendly-error", handleApiError);

    return () => {
      window.removeEventListener("api:friendly-error", handleApiError);
      window.clearTimeout(timeoutRef.current);
    };
  }, []);

  if (!message) return null;

  return (
    <div className="global-api-toast" role="alert" aria-live="assertive">
      <span>{message}</span>
      <button
        type="button"
        className="global-api-toast__close"
        onClick={() => setMessage("")}
        aria-label="Dismiss notification"
      >
        x
      </button>
    </div>
  );
}

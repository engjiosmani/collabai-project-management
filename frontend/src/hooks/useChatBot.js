import { useCallback, useContext, useEffect, useRef, useState } from "react";

import { getApiErrorMessage } from "../api/api";
import { sendChatBotMessage } from "../api/chatbot";
import { AuthContext } from "../context/AuthContext";

export function useChatBot() {
  const { user } = useContext(AuthContext);
  const chatEndRef = useRef(null);
  const abortRef = useRef(null);

  const [input, setInput] = useState("");
  const [turns, setTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  const displayName = user?.email ? user.email.split("@")[0] : "";

  const clearChat = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setTurns([]);
    setError("");
    setInput("");
    setLoading(false);
  }, []);

  const abortOnUnmount = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = (text || "").trim();
      if (!trimmed || loading) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setInput("");
      setError("");
      setLoading(true);
      setTurns((prev) => [...prev, { role: "user", text: trimmed }]);

      const history = turns.flatMap((t) => [
        { role: t.role, content: t.text },
      ]);

      try {
        const data = await sendChatBotMessage({
          message: trimmed,
          history,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setTurns((prev) => [
          ...prev,
          { role: "assistant", text: data.answer || "" },
        ]);
      } catch (err) {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setError(
          getApiErrorMessage(
            err,
            "No response. Check backend and GROQ_API_KEY in backend/.env."
          )
        );
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setLoading(false);
      }
    },
    [loading, turns]
  );

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (loading) {
      abortRef.current?.abort();
      setLoading(false);
      return;
    }
    sendMessage(input);
  };

  return {
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
    isEmpty: turns.length === 0,
  };
}

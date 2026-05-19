import { useCallback, useContext, useEffect, useRef, useState } from "react";

import { getApiErrorMessage } from "../api/api";
import { fetchWorkspaces, ragQuery, reindexWorkspace } from "../api/ai";
import { AuthContext } from "../context/AuthContext";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

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

export function docTypeLabel(type) {
  return DOC_TYPE_LABELS[type] || type;
}

export function formatScore(score) {
  if (score == null) return null;
  return `${Math.round(Number(score) * 100)}% match`;
}

export { EXAMPLE_QUESTIONS };

export function useAIAssistantChat() {
  const { user } = useContext(AuthContext);
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
          getApiErrorMessage(
            err,
            "No response received. Check that the backend is running and GROQ_API_KEY is set in backend/.env."
          )
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

  const abortOnUnmount = useCallback(() => {
    chatAbortRef.current?.abort();
  }, []);

  const isEmpty = chatTurns.length === 0;
  const hasWorkspace = Boolean(wsId);
  const displayName = user?.email ? user.email.split("@")[0] : "";

  return {
    user,
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
    wsId,
    workspaceLabel,
    stopGeneration,
    handleSubmit,
    handleExample,
    handleReindex,
    clearChat,
    abortOnUnmount,
    isEmpty,
    hasWorkspace,
    displayName,
  };
}

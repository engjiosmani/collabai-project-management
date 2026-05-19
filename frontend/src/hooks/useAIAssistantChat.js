import { useCallback, useContext, useEffect, useRef, useState } from "react";

import { getApiErrorMessage } from "../api/api";
import { ragQuery, reindexOrganization } from "../api/ai";
import { fetchProjects, projectLabel } from "../api/projects";
import { AuthContext } from "../context/AuthContext";

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

  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(true);

  const [input, setInput] = useState("");
  const [chatTurns, setChatTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setProjectsLoading(true);
      try {
        const list = await fetchProjects();
        if (cancelled) return;
        setProjects(list);
        if (list.length > 0) setProjectId(String(list[0].id));
      } catch (err) {
        if (!cancelled) {
          setError(getApiErrorMessage(err, "Could not load projects."));
        }
      } finally {
        if (!cancelled) setProjectsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatTurns, loading]);

  const selectedProject = projects.find((p) => String(p.id) === projectId);
  const organizationId = selectedProject?.organization ?? null;
  const orgId = organizationId != null ? Number(organizationId) : null;
  const selectedProjectLabel = projectLabel(selectedProject);

  const stopGeneration = useCallback(() => {
    chatAbortRef.current?.abort();
  }, []);

  const isAbortError = (err) =>
    err?.code === "ERR_CANCELED" ||
    err?.name === "CanceledError" ||
    err?.message === "canceled";

  const runChat = useCallback(
    async (text) => {
      if (!orgId || !text.trim() || loading) return;
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
          organizationId: orgId,
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
    [orgId, loading]
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
    if (!orgId) return;
    setReindexing(true);
    setError("");
    try {
      await reindexOrganization(orgId);
      setShowSettings(false);
    } catch (err) {
      setError(getApiErrorMessage(err, "Update failed."));
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
  const hasProject = Boolean(orgId && selectedProject);
  const displayName = user?.email ? user.email.split("@")[0] : "";

  return {
    user,
    chatEndRef,
    projects,
    projectId,
    setProjectId,
    projectsLoading,
    input,
    setInput,
    chatTurns,
    loading,
    reindexing,
    showSettings,
    setShowSettings,
    error,
    setError,
    orgId,
    selectedProject,
    selectedProjectLabel,
    stopGeneration,
    handleSubmit,
    handleExample,
    handleReindex,
    clearChat,
    abortOnUnmount,
    isEmpty,
    hasProject,
    displayName,
  };
}

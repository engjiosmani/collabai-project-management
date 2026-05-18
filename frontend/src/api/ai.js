import API from "./api";

export async function fetchWorkspaces() {
  const { data } = await API.get("/workspaces/");
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function semanticSearch({ workspaceId, query, topK = 8 }) {
  const { data } = await API.post("/ai/search/", {
    workspace_id: workspaceId,
    query,
    top_k: topK,
  });
  return data;
}

export async function ragQuery({
  workspaceId,
  question,
  topK = 5,
  taskId = null,
  signal = null,
}) {
  const payload = {
    workspace_id: workspaceId,
    question,
    top_k: topK,
  };
  if (taskId) {
    payload.task_id = taskId;
  }
  const config = signal ? { signal } : {};
  const { data } = await API.post("/ai/query/", payload, config);
  return data;
}

export async function reindexWorkspace(workspaceId) {
  const { data } = await API.post("/ai/reindex/", { workspace_id: workspaceId });
  return data;
}

export async function fetchAIHistory() {
  const { data } = await API.get("/ai/history/");
  return data;
}

import API from "./api";

export async function semanticSearch({ organizationId, query, topK = 8 }) {
  const { data } = await API.post("/ai/search/", {
    organization_id: organizationId,
    query,
    top_k: topK,
  });
  return data;
}

export async function ragQuery({
  organizationId,
  question,
  topK = 5,
  taskId = null,
  signal = null,
}) {
  const payload = {
    organization_id: organizationId,
    question,
    top_k: topK,
  };
  if (taskId) {
    payload.task_id = taskId;
  }
  const config = {
    timeout: 120000,
    ...(signal ? { signal } : {}),
  };
  const { data } = await API.post("/ai/query/", payload, config);
  return data;
}

export async function reindexOrganization(organizationId) {
  const { data } = await API.post("/ai/reindex/", { organization_id: organizationId });
  return data;
}

export async function fetchAIHistory() {
  const { data } = await API.get("/ai/history/");
  return data;
}

export async function analyzeText({ text, mode = "summary", taskId = null }) {
  const payload = { text, mode };
  if (taskId != null) {
    payload.task_id = taskId;
  }
  const { data } = await API.post("/ai/analyze/", payload, { timeout: 120000 });
  return data;
}

import API, { getApiErrorMessage } from "./api";

export async function fetchTeamPulseOverview(workspaceId) {
  const { data } = await API.get("/ai/team-pulse/", {
    params: { workspace_id: workspaceId },
  });
  return data;
}

export async function saveGitHubConfig(payload) {
  const { data } = await API.put("/ai/team-pulse/github/", payload);
  return data;
}

export async function runTeamPulse(workspaceId, runType = "both") {
  const { data } = await API.post("/ai/team-pulse/run/", {
    workspace_id: workspaceId,
    run_type: runType,
  });
  return data;
}

export async function dismissTeamPulseAlert(alertId) {
  const { data } = await API.post(`/ai/team-pulse/alerts/${alertId}/dismiss/`);
  return data;
}

export { getApiErrorMessage };

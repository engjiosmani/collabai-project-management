import API, { getApiErrorMessage } from "./api";

export async function fetchOrganizationMembers(organizationId) {
  const { data } = await API.get(`/organizations/${organizationId}/members/`);
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function fetchTeamPulseOverview(organizationId) {
  const { data } = await API.get("/ai/team-pulse/", {
    params: { organization_id: organizationId },
  });
  return data;
}

export async function saveGitHubConfig(payload) {
  const { data } = await API.put("/ai/team-pulse/github/", payload);
  return data;
}

export async function runTeamPulse(organizationId, runType = "standup") {
  const { data } = await API.post("/ai/team-pulse/run/", {
    organization_id: organizationId,
    run_type: runType,
  });
  return data;
}

export { getApiErrorMessage };

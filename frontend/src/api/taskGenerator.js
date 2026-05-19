import API, { getApiErrorMessage } from "./api";

export { getApiErrorMessage };

export async function fetchAIConfig() {
  const { data } = await API.get("/ai/config/");
  return data;
}

export async function fetchWorkspaceMembers(workspaceId) {
  const { data } = await API.get(`/workspaces/${workspaceId}/members/`);
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function fetchJobRoles() {
  const { data } = await API.get("/job-roles/");
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function updateMemberJobRole(workspaceId, memberId, jobRoleId) {
  const { data } = await API.patch(
    `/workspaces/${workspaceId}/members/${memberId}/job-role/`,
    { job_role_id: jobRoleId }
  );
  return data;
}

export async function fetchWorkspaceProjects(workspaceId) {
  const { data } = await API.get("/projects/", {
    params: { workspace: workspaceId },
  });
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function createTaskPlan({
  workspaceId,
  description,
  sprintCount,
  teamMembers,
  targetProjectId = null,
}) {
  const payload = {
    workspace_id: workspaceId,
    description,
    sprint_count: sprintCount,
    team_members: teamMembers,
  };
  if (targetProjectId) {
    payload.target_project_id = targetProjectId;
  }
  const { data } = await API.post("/ai/task-generator/plans/", payload);
  return data;
}

export async function fetchTaskPlan(planId) {
  const { data } = await API.get(`/ai/task-generator/plans/${planId}/`);
  return data;
}

export async function fetchTaskPlanStatus(planId) {
  const { data } = await API.get(`/ai/task-generator/plans/${planId}/status/`);
  return data;
}

export async function approveTaskPlan(planId, { targetProjectId } = {}) {
  const payload =
    targetProjectId !== undefined
      ? { target_project_id: targetProjectId }
      : {};
  const { data } = await API.post(`/ai/task-generator/plans/${planId}/approve/`, payload);
  return data;
}

export async function rejectTaskPlan(planId) {
  await API.delete(`/ai/task-generator/plans/${planId}/reject/`);
}

export async function updatePlannedTask(planId, taskId, payload) {
  const { data } = await API.patch(
    `/ai/task-generator/plans/${planId}/tasks/${taskId}/`,
    payload
  );
  return data;
}

export async function regeneratePlannedTask(planId, taskId, hint = "") {
  const { data } = await API.post(
    `/ai/task-generator/plans/${planId}/tasks/${taskId}/regenerate/`,
    { hint }
  );
  return data;
}

export async function fetchPlanPreviewMarkdown(planId) {
  const { data } = await API.get(`/ai/task-generator/plans/${planId}/preview-markdown/`);
  return data;
}

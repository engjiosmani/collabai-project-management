import API, { getApiErrorMessage } from "./api";

export { getApiErrorMessage };

export async function fetchAIConfig() {
  const { data } = await API.get("/ai/config/");
  return data;
}

export async function fetchOrganizationMembers(organizationId) {
  const { data } = await API.get(`/organizations/${organizationId}/members/`);
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function fetchJobRoles() {
  const { data } = await API.get("/job-roles/");
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function updateMemberJobRole(organizationId, memberId, jobRoleId) {
  const { data } = await API.patch(
    `/organizations/${organizationId}/members/${memberId}/job-role/`,
    { job_role_id: jobRoleId }
  );
  return data;
}

export async function fetchOrganizationProjects(organizationId) {
  const { data } = await API.get("/projects/", {
    params: { organization: organizationId },
  });
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function createTaskPlan({
  organizationId,
  description,
  sprintCount,
  teamMembers,
  targetProjectId = null,
}) {
  const payload = {
    organization_id: organizationId,
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

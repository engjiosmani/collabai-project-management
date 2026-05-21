import API from "./api";

const unwrap = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

export const getOrganizations = async () => {
  const res = await API.get("/organizations/");
  return unwrap(res.data);
};

export const createOrganization = async (payload) => {
  const res = await API.post("/organizations/", payload);
  return res.data;
};

export const updateOrganization = async (organizationId, payload) => {
  const res = await API.patch(`/organizations/${organizationId}/`, payload);
  return res.data;
};

export const getOrganizationMembers = async (organizationId) => {
  const res = await API.get(`/organizations/${organizationId}/members/`);
  return unwrap(res.data);
};

export const inviteOrganizationMember = async (organizationId, payload) => {
  const res = await API.post(`/organizations/${organizationId}/invite/`, payload);
  return res.data;
};

export const updateOrganizationMember = async (organizationId, userId, payload) => {
  const res = await API.patch(
    `/organizations/${organizationId}/members/${userId}/`,
    payload
  );
  return res.data;
};

export const removeOrganizationMember = async (organizationId, userId) => {
  await API.delete(`/organizations/${organizationId}/members/${userId}/`);
};

export const getOrganizationWorkspaces = async (organizationId) => {
  const res = await API.get(`/organizations/${organizationId}/workspaces/`);
  return unwrap(res.data);
};

export const createWorkspace = async (organizationId, payload) => {
  const res = await API.post(
    `/organizations/${organizationId}/workspaces/`,
    payload
  );
  return res.data;
};

export const getWorkspaceMembers = async (organizationId, workspaceId) => {
  const res = await API.get(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members/`
  );
  return unwrap(res.data);
};

export const addWorkspaceMember = async (organizationId, workspaceId, payload) => {
  const res = await API.post(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members/`,
    payload
  );
  return res.data;
};

export const updateWorkspaceMember = async (
  organizationId,
  workspaceId,
  userId,
  payload
) => {
  const res = await API.patch(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members/${userId}/`,
    payload
  );
  return res.data;
};

export const removeWorkspaceMember = async (organizationId, workspaceId, userId) => {
  await API.delete(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members/${userId}/`
  );
};

export const getOrganizationInvites = async (organizationId) => {
  const res = await API.get(`/organizations/${organizationId}/invites/`);
  return Array.isArray(res.data) ? res.data : res.data?.results || [];
};

export const removeOrganizationInvite = async (organizationId, inviteId) => {
  await API.delete(`/organizations/${organizationId}/invites/${inviteId}/`);
};
export const getMyInvitations = async () => {
  const res = await API.get("/invites/my/");
  return Array.isArray(res.data) ? res.data : res.data?.results || [];
};

export const acceptInvite = async (token) => {
  const res = await API.post(`/invites/${token}/accept/`);
  return res.data;
};
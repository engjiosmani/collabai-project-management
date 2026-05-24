import API from "./api";

const unwrap = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

export const getWorkspaceMembers = async (workspaceId) => {
  const res = await API.get(`/workspaces/${workspaceId}/members/`);
  return unwrap(res.data).map((member) => ({
    ...member,
    user_id: member.user_id ?? member.user?.id ?? member.user ?? "",
    username: member.username ?? member.user?.username ?? member.user_email?.split("@")[0] ?? member.email?.split("@")[0] ?? "",
    email: member.email ?? member.user_email ?? member.user?.email ?? "",
  }));
};

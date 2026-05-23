import API from "../api/api";

const unwrapList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

export const getProfile = async () => {
  const response = await API.get("/profile/");
  return response.data;
};

export const updateProfile = async (payload) => {
  const response = await API.patch("/profile/", payload);
  return response.data;
};

export const updateProfileAvatar = async (file) => {
  const formData = new FormData();
  formData.append("avatar", file);

  const response = await API.patch("/profile/", formData);
  return response.data;
};

export const changePassword = async (payload) => {
  const response = await API.post("/profile/change-password/", {
    old_password: payload.current_password,
    new_password: payload.new_password,
    confirm_password: payload.confirm_password,
  });
  return response.data;
};

export const getMemberships = async () => {
  const response = await API.get("/profile/memberships/");
  return unwrapList(response.data);
};

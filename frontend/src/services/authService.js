import API from "../api/api";

export const requestPasswordReset = async (email) => {
  const response = await API.post("/auth/forgot-password", { email });
  return response.data;
};

export const resetPassword = async ({ token, password, confirm_password }) => {
  try {
    const response = await API.post("/auth/reset-password", {
      token,
      password,
      confirm_password,
    });
    return response.data;
  } catch (error) {
    const data = error.response?.data;
    const requiresLegacyField =
      error.response?.status === 400 &&
      data &&
      Object.prototype.hasOwnProperty.call(data, "new_password");

    if (!requiresLegacyField) {
      throw error;
    }

    const response = await API.post("/auth/reset-password", {
      token,
      new_password: password,
    });
    return response.data;
  }
};

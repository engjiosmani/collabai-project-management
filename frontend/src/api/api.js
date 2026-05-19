import axios from "axios";

const baseURL = (
  process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

const API = axios.create({ baseURL });

let isRefreshing = false;
let refreshWaitQueue = [];

const processRefreshQueue = (error, accessToken = null) => {
  refreshWaitQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(accessToken);
  });
  refreshWaitQueue = [];
};

/** Extract a human-readable message from a DRF/axios error. */
export function getApiErrorMessage(err, fallback = "Something went wrong.") {
  if (!err?.response) {
    return err?.message || "Cannot reach the backend. Is runserver running on port 8000?";
  }
  const data = err.response.data;
  if (!data) return fallback;
  if (typeof data === "string") {
    if (data.includes("<!DOCTYPE html>") || data.includes("<html")) {
      const titleMatch = data.match(/<title>\s*([^<]+?)\s*<\/title>/i);
      if (titleMatch) {
        return titleMatch[1].replace(/\s+at\s+\/api\/.*/i, "").trim();
      }
    }
    return data.length > 200 ? `${data.slice(0, 200)}…` : data;
  }
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) return String(data.detail[0]);
  if (typeof data === "object") {
    const firstKey = Object.keys(data)[0];
    const val = data[firstKey];
    if (Array.isArray(val) && val.length) return `${firstKey}: ${val[0]}`;
    if (typeof val === "string") return `${firstKey}: ${val}`;
  }
  return fallback;
}

export const clearAuthStorage = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("user_email");
  window.dispatchEvent(new Event("auth:logout"));
};

const redirectToLogin = () => {
  clearAuthStorage();
  if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
    window.location.href = "/login";
  }
};

const isAuthEndpoint = (url = "") => {
  const path = String(url);
  return (
    path.includes("/auth/login") ||
    path.includes("/auth/register") ||
    path.includes("/auth/refresh")
  );
};

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");

  if (token && !config.headers?.Authorization) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }

  return config;
});

API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    if (
      !originalRequest ||
      status !== 401 ||
      originalRequest._authRetry ||
      isAuthEndpoint(originalRequest.url)
    ) {
      return Promise.reject(error);
    }

    const refresh = localStorage.getItem("refresh");
    if (!refresh) {
      redirectToLogin();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshWaitQueue.push({ resolve, reject });
      }).then((newAccess) => {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return API(originalRequest);
      });
    }

    originalRequest._authRetry = true;
    isRefreshing = true;

    try {
      const { data } = await axios.post(
        `${baseURL}/auth/refresh`,
        { refresh },
        { headers: { "Content-Type": "application/json" } }
      );

      const newAccess = data.access;
      localStorage.setItem("access", newAccess);
      window.dispatchEvent(
        new CustomEvent("auth:token-refreshed", { detail: { access: newAccess } })
      );

      processRefreshQueue(null, newAccess);
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return API(originalRequest);
    } catch (refreshError) {
      processRefreshQueue(refreshError, null);
      redirectToLogin();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default API;

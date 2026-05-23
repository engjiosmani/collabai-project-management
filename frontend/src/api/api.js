import axios from "axios";

const baseURL = (
  process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

const API = axios.create({
  baseURL,
  // Local dashboard queries can exceed 15s on a cold DB; avoid false "unreachable" errors.
  timeout: 60000,
});

let isRefreshing = false;
let refreshWaitQueue = [];

const RATE_LIMIT_MESSAGE =
  "Too many requests — please wait a moment before trying again.";
const NETWORK_ERROR_MESSAGE =
  "Cannot reach the backend. Please check your connection and try again.";
const TIMEOUT_MESSAGE =
  "The server is taking too long to respond. Please try again in a moment.";

let lastGlobalErrorMessage = "";
let lastGlobalErrorAt = 0;

const isTimeoutError = (err) =>
  err?.code === "ECONNABORTED" || err?.message?.toLowerCase().includes("timeout");

const transportErrorMessage = (err) =>
  isTimeoutError(err) ? TIMEOUT_MESSAGE : NETWORK_ERROR_MESSAGE;

const showGlobalApiError = (message) => {
  if (typeof window === "undefined" || !message) return;

  const now = Date.now();
  if (message === lastGlobalErrorMessage && now - lastGlobalErrorAt < 3000) {
    return;
  }

  lastGlobalErrorMessage = message;
  lastGlobalErrorAt = now;

  const event = new CustomEvent("api:friendly-error", {
    detail: { message },
    cancelable: true,
  });

  const shouldUseFallbackAlert = window.dispatchEvent(event);
  if (shouldUseFallbackAlert && typeof window.alert === "function") {
    window.alert(message);
  }
};

const processRefreshQueue = (error, accessToken = null) => {
  refreshWaitQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(accessToken);
  });
  refreshWaitQueue = [];
};

/** Extract a human-readable message from a DRF/axios error. */
export function getApiErrorMessage(err, fallback = "Something went wrong.") {
  if (err?.friendlyMessage) {
    return err.friendlyMessage;
  }
  if (!err?.response) {
    return transportErrorMessage(err);
  }
  if (err.response.status === 429) return RATE_LIMIT_MESSAGE;
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
  localStorage.removeItem("active_organization_id");
  localStorage.removeItem("active_workspace_id");
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
  const organizationId = localStorage.getItem("active_organization_id");
  const isAuthRequest = isAuthEndpoint(config.url);

  if (!isAuthRequest && token && !config.headers?.Authorization) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }

  if (!isAuthRequest && token && organizationId && !config.headers?.["X-Organization-ID"]) {
    config.headers = {
      ...config.headers,
      "X-Organization-ID": organizationId,
    };
  }

  return config;
});

API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    if (!error.response) {
      error.friendlyMessage = transportErrorMessage(error);
      return Promise.reject(error);
    }

    if (status === 429) {
      error.friendlyMessage = RATE_LIMIT_MESSAGE;
      showGlobalApiError(RATE_LIMIT_MESSAGE);
      return Promise.reject(error);
    }

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
      window.dispatchEvent(new Event("auth:token-refreshed"));

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

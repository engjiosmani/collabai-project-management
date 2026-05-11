import axios from "axios";

const API = axios.create({
  baseURL:
    (process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, ""),
});

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

export default API;
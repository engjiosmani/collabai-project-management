import API from "./api";

const unwrap = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

export const getTasks = async (params = {}, signal) => {
  const res = await API.get("/tasks/", { params, signal });
  return unwrap(res.data);
};

export const getTaskStatuses = async (signal) => {
  const res = await API.get("/task-statuses/", { signal });
  return unwrap(res.data);
};

export const getTaskPriorities = async (signal) => {
  const res = await API.get("/task-priorities/", { signal });
  return unwrap(res.data);
};

export const createTask = async (payload) => {
  const res = await API.post("/tasks/", payload);
  return res.data;
};

export const updateTask = async (taskId, payload) => {
  const res = await API.patch(`/tasks/${taskId}/`, payload);
  return res.data;
};

export const deleteTask = async (taskId) => {
  await API.delete(`/tasks/${taskId}/`);
};

export const getTaskAttachments = async (taskId, signal) => {
  const res = await API.get(`/tasks/${taskId}/attachments/`, { signal });
  return unwrap(res.data);
};

export const downloadTaskAttachment = async (taskId, attachmentId) => {
  const res = await API.get(`/tasks/${taskId}/attachments/${attachmentId}/download/`, {
    responseType: "blob",
  });
  return res.data;
};

export const deleteTaskAttachment = async (taskId, attachmentId) => {
  await API.delete(`/tasks/${taskId}/attachments/${attachmentId}/`);
};

export const uploadTaskAttachment = async (taskId, file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await API.post(`/tasks/${taskId}/attachments/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const getTaskComments = async (taskId, signal) => {
  const res = await API.get("/comments/", {
    params: { task: taskId, ordering: "created_at" },
    signal,
  });
  return unwrap(res.data);
};

export const createTaskComment = async (payload) => {
  const res = await API.post("/comments/", payload);
  return res.data;
};

export const getTaskActivityLogs = async (taskId, signal) => {
  const res = await API.get("/activity-logs/", {
    params: { task: taskId, ordering: "-created_at" },
    signal,
  });
  return unwrap(res.data);
};
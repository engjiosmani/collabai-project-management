import API from "./api";

export const unwrapNotificationPage = (data) => {
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data,
    };
  }

  return {
    count: data?.count ?? 0,
    next: data?.next ?? null,
    previous: data?.previous ?? null,
    results: data?.results ?? [],
  };
};

export const fetchNotifications = async (params = {}, signal) => {
  const { data } = await API.get("/notifications/", { params, signal });
  return unwrapNotificationPage(data);
};

export const fetchLatestNotifications = async (signal) => {
  const page = await fetchNotifications(
    { page_size: 10, ordering: "-created_at" },
    signal
  );
  return page.results;
};

export const fetchUnreadNotificationCount = async (signal) => {
  const page = await fetchNotifications(
    { is_read: false, page_size: 1 },
    signal
  );
  return page.count;
};

export const markNotificationRead = async (notificationId) => {
  const { data } = await API.post(`/notifications/${notificationId}/mark_read/`);
  return data;
};

export const markAllNotificationsRead = async () => {
  const { data } = await API.post("/notifications/mark_all_read/");
  return data;
};

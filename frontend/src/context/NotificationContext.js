import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  fetchLatestNotifications,
  fetchUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/notifications";
import { getApiErrorMessage } from "../api/api";
import { AuthContext } from "./AuthContext";

const POLL_INTERVAL_MS = 60000;

const NotificationContext = createContext(null);

const showToast = (message, tone = "error") => {
  if (!message || typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("app:toast", {
      detail: { message, tone },
    })
  );
};

export function NotificationProvider({ children }) {
  const { accessToken } = useContext(AuthContext);
  const [unreadCount, setUnreadCount] = useState(0);
  const [latestNotifications, setLatestNotifications] = useState([]);
  const [loadingLatest, setLoadingLatest] = useState(false);
  const [latestError, setLatestError] = useState("");
  const [markingAllRead, setMarkingAllRead] = useState(false);
  const pollingRef = useRef(null);
  const countControllerRef = useRef(null);
  const latestControllerRef = useRef(null);
  const unreadCountRef = useRef(0);
  const latestNotificationsRef = useRef([]);

  useEffect(() => {
    unreadCountRef.current = unreadCount;
  }, [unreadCount]);

  useEffect(() => {
    latestNotificationsRef.current = latestNotifications;
  }, [latestNotifications]);

  const resetState = useCallback(() => {
    setUnreadCount(0);
    setLatestNotifications([]);
    setLoadingLatest(false);
    setLatestError("");
    setMarkingAllRead(false);
  }, []);

  const refreshUnreadCount = useCallback(
    async ({ signal, silent = true } = {}) => {
      if (!accessToken) {
        setUnreadCount(0);
        return 0;
      }

      try {
        const count = await fetchUnreadNotificationCount(signal);
        if (!signal?.aborted) {
          setUnreadCount(count);
        }
        return count;
      } catch (err) {
        if (signal?.aborted || err?.code === "ERR_CANCELED") {
          return unreadCountRef.current;
        }
        if (!silent) {
          showToast(getApiErrorMessage(err, "Unable to load notifications."));
        }
        return unreadCountRef.current;
      }
    },
    [accessToken]
  );

  const refreshLatest = useCallback(
    async ({ signal, silent = false } = {}) => {
      if (!accessToken) {
        resetState();
        return [];
      }

      if (!silent) {
        setLoadingLatest(true);
      }
      setLatestError("");

      try {
        const data = await fetchLatestNotifications(signal);
        if (!signal?.aborted) {
          setLatestNotifications(data);
        }
        return data;
      } catch (err) {
        if (signal?.aborted || err?.code === "ERR_CANCELED") {
          return latestNotificationsRef.current;
        }
        const message = getApiErrorMessage(err, "Unable to load notifications.");
        setLatestError(message);
        if (!silent) showToast(message);
        return latestNotificationsRef.current;
      } finally {
        if (!signal?.aborted && !silent) {
          setLoadingLatest(false);
        }
      }
    },
    [accessToken, resetState]
  );

  const markAsRead = useCallback(
    async (notification) => {
      if (!notification?.id) return null;

      const wasUnread = !notification.is_read;
      const previousNotifications = latestNotifications;
      const previousCount = unreadCount;

      if (wasUnread) {
        setLatestNotifications((items) =>
          items.map((item) =>
            item.id === notification.id ? { ...item, is_read: true } : item
          )
        );
        setUnreadCount((count) => Math.max(count - 1, 0));
      }

      try {
        const updated = await markNotificationRead(notification.id);
        setLatestNotifications((items) =>
          items.map((item) => (item.id === notification.id ? updated : item))
        );
        return updated;
      } catch (err) {
        setLatestNotifications(previousNotifications);
        setUnreadCount(previousCount);
        showToast(getApiErrorMessage(err, "Unable to mark notification as read."));
        throw err;
      }
    },
    [latestNotifications, unreadCount]
  );

  const markAllAsRead = useCallback(async () => {
    if (!accessToken || markingAllRead) return;

    const previousNotifications = latestNotifications;
    const previousCount = unreadCount;

    setMarkingAllRead(true);
    setLatestNotifications((items) =>
      items.map((item) => ({ ...item, is_read: true }))
    );
    setUnreadCount(0);

    try {
      await markAllNotificationsRead();
      showToast("All notifications marked as read.", "success");
    } catch (err) {
      setLatestNotifications(previousNotifications);
      setUnreadCount(previousCount);
      showToast(getApiErrorMessage(err, "Unable to mark all notifications as read."));
      throw err;
    } finally {
      setMarkingAllRead(false);
    }
  }, [accessToken, latestNotifications, markingAllRead, unreadCount]);

  useEffect(() => {
    countControllerRef.current?.abort();
    latestControllerRef.current?.abort();

    if (!accessToken) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
      resetState();
      return undefined;
    }

    const countController = new AbortController();
    countControllerRef.current = countController;
    refreshUnreadCount({ signal: countController.signal, silent: true });

    window.clearInterval(pollingRef.current);
    pollingRef.current = window.setInterval(() => {
      countControllerRef.current?.abort();
      const nextController = new AbortController();
      countControllerRef.current = nextController;
      refreshUnreadCount({ signal: nextController.signal, silent: true });
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
      countController.abort();
      countControllerRef.current?.abort();
    };
  }, [accessToken, refreshUnreadCount, resetState]);

  useEffect(() => {
    const refreshForOrganization = () => {
      if (!accessToken) return;
      countControllerRef.current?.abort();
      latestControllerRef.current?.abort();

      const countController = new AbortController();
      const latestController = new AbortController();
      countControllerRef.current = countController;
      latestControllerRef.current = latestController;

      refreshUnreadCount({ signal: countController.signal, silent: true });
      refreshLatest({ signal: latestController.signal, silent: true });
    };

    window.addEventListener("organization:changed", refreshForOrganization);
    return () => {
      window.removeEventListener("organization:changed", refreshForOrganization);
    };
  }, [accessToken, refreshLatest, refreshUnreadCount]);

  const value = useMemo(
    () => ({
      unreadCount,
      latestNotifications,
      loadingLatest,
      latestError,
      markingAllRead,
      refreshUnreadCount,
      refreshLatest,
      markAsRead,
      markAllAsRead,
    }),
    [
      latestError,
      latestNotifications,
      loadingLatest,
      markAllAsRead,
      markAsRead,
      markingAllRead,
      refreshLatest,
      refreshUnreadCount,
      unreadCount,
    ]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}

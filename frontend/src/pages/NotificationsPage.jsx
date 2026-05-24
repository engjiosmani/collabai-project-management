import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { fetchNotifications } from "../api/notifications";
import { getApiErrorMessage } from "../api/api";
import AppSidebar from "../components/AppSidebar";
import NotificationList from "../components/notifications/NotificationList";
import { useNotifications } from "../hooks/useNotifications";
import { getNotificationTarget } from "../utils/notificationActions";
import "./Dashboard.css";

const PAGE_SIZE = 20;

function normalizePageNumber(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

function NotificationsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = normalizePageNumber(searchParams.get("page"));
  const filter = searchParams.get("filter") || "all";
  const { markAsRead, markAllAsRead, markingAllRead, unreadCount } = useNotifications();
  const [pageData, setPageData] = useState({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const params = useMemo(() => {
    const next = { page, page_size: PAGE_SIZE, ordering: "-created_at" };
    if (filter === "unread") next.is_read = false;
    if (filter === "read") next.is_read = true;
    return next;
  }, [filter, page]);

  const loadPage = useCallback(
    async ({ signal } = {}) => {
      setLoading(true);
      setError("");

      try {
        const data = await fetchNotifications(params, signal);
        if (!signal?.aborted) {
          setPageData(data);
        }
      } catch (err) {
        if (signal?.aborted || err?.code === "ERR_CANCELED") return;
        setError(getApiErrorMessage(err, "Unable to load notifications."));
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
        }
      }
    },
    [params]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadPage({ signal: controller.signal });
    return () => controller.abort();
  }, [loadPage]);

  const updatePageParam = (nextPage) => {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete("page");
    else next.set("page", String(nextPage));
    setSearchParams(next);
  };

  const updateFilter = (nextFilter) => {
    const next = new URLSearchParams(searchParams);
    if (nextFilter === "all") next.delete("filter");
    else next.set("filter", nextFilter);
    next.delete("page");
    setSearchParams(next);
  };

  const handleSelect = async (notification) => {
    if (!notification) return;

    try {
      const updated = await markAsRead(notification);
      setPageData((current) => ({
        ...current,
        count: filter === "unread" ? Math.max(current.count - 1, 0) : current.count,
        results:
          filter === "unread"
            ? current.results.filter((item) => item.id !== notification.id)
            : current.results.map((item) =>
                item.id === notification.id
                  ? updated || { ...item, is_read: true }
                  : item
              ),
      }));
    } catch {
      return;
    }

    const target = getNotificationTarget(notification);
    if (target) navigate(target);
  };

  const handleMarkAll = async () => {
    try {
      await markAllAsRead();
      setPageData((current) => ({
        ...current,
        count: filter === "unread" ? 0 : current.count,
        results:
          filter === "unread"
            ? []
            : current.results.map((item) => ({ ...item, is_read: true })),
      }));
    } catch {
      // The provider restores shared state and shows the toast.
    }
  };

  const totalPages = Math.max(1, Math.ceil(pageData.count / PAGE_SIZE));
  const hasPrevious = Boolean(pageData.previous) || page > 1;
  const hasNext = Boolean(pageData.next) || page < totalPages;

  return (
    <div className="dashboard-shell">
      <AppSidebar />

      <main className="dashboard-main">
        <header className="dashboard-topbar">
          <div>
            <h2 className="dashboard-heading">Notifications</h2>
            <p className="dashboard-subheading">
              Review task, comment, invite, and system updates across your active scope.
            </p>
          </div>

          <div className="dashboard-meta">
            <span className="dashboard-status-pill">
              {unreadCount ? `${unreadCount} unread` : "All read"}
            </span>
            <button
              className="dashboard-button dashboard-button--ghost"
              type="button"
              onClick={() => loadPage()}
              disabled={loading}
            >
              Refresh
            </button>
            <button
              className="dashboard-button dashboard-button--primary"
              type="button"
              onClick={handleMarkAll}
              disabled={!unreadCount || markingAllRead}
            >
              {markingAllRead ? "Saving" : "Mark all as read"}
            </button>
          </div>
        </header>

        <section className="notifications-page-toolbar" aria-label="Notification filters">
          {["all", "unread", "read"].map((option) => (
            <button
              key={option}
              type="button"
              className={`notifications-filter${
                filter === option ? " notifications-filter--active" : ""
              }`}
              onClick={() => updateFilter(option)}
            >
              {option[0].toUpperCase() + option.slice(1)}
            </button>
          ))}
        </section>

        <section className="dashboard-panel dashboard-panel--wide notifications-page-panel">
          <NotificationList
            notifications={pageData.results}
            loading={loading}
            error={error}
            onRetry={() => loadPage()}
            onSelect={handleSelect}
          />
        </section>

        {!loading && !error && pageData.count > PAGE_SIZE ? (
          <nav className="notifications-pagination" aria-label="Notifications pages">
            <button
              type="button"
              className="dashboard-button dashboard-button--ghost"
              onClick={() => updatePageParam(page - 1)}
              disabled={!hasPrevious}
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className="dashboard-button dashboard-button--ghost"
              onClick={() => updatePageParam(page + 1)}
              disabled={!hasNext}
            >
              Next
            </button>
          </nav>
        ) : null}
      </main>
    </div>
  );
}

export default NotificationsPage;

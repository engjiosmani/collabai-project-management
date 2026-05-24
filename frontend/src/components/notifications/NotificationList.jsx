import EmptyState from "../ui/EmptyState";
import LoadingSkeleton from "../ui/LoadingSkeleton";
import NotificationItem from "./NotificationItem";

function NotificationList({
  notifications = [],
  loading = false,
  error = "",
  onRetry,
  onSelect,
  compact = false,
}) {
  if (loading) {
    return (
      <LoadingSkeleton
        variant="list"
        count={compact ? 3 : 5}
        lines={2}
        label="Loading notifications"
      />
    );
  }

  if (error) {
    return (
      <EmptyState
        compact={compact}
        icon="!"
        title="Notifications could not load"
        description={error}
        actionLabel={onRetry ? "Try again" : undefined}
        onAction={onRetry}
        actionClassName="dashboard-button dashboard-button--ghost"
      />
    );
  }

  if (!notifications.length) {
    return (
      <EmptyState
        compact={compact}
        icon="N"
        title="You're all caught up"
        description="Updates that need your attention will appear here."
      />
    );
  }

  return (
    <ul className="notification-list" aria-label="Notifications">
      {notifications.map((notification) => (
        <li key={notification.id}>
          <NotificationItem
            compact={compact}
            notification={notification}
            onSelect={onSelect}
          />
        </li>
      ))}
    </ul>
  );
}

export default NotificationList;

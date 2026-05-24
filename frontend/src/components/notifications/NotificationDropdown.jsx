import { Link } from "react-router-dom";

import NotificationList from "./NotificationList";

function NotificationDropdown({
  notifications,
  loading,
  error,
  unreadCount,
  markingAllRead,
  onRetry,
  onMarkAllRead,
  onSelect,
  onClose,
  panelId,
  style,
}) {
  return (
    <section
      id={panelId}
      className="notification-dropdown"
      style={style}
      role="dialog"
      aria-label="Notification center"
    >
      <div className="notification-dropdown__header">
        <div>
          <h2>Notifications</h2>
          <p>{unreadCount ? `${unreadCount} unread` : "You're all caught up"}</p>
        </div>
        <button
          type="button"
          className="notification-dropdown__mark-all"
          onClick={onMarkAllRead}
          disabled={!unreadCount || markingAllRead}
        >
          {markingAllRead ? "Saving" : "Mark all as read"}
        </button>
      </div>

      <div className="notification-dropdown__body">
        <NotificationList
          compact
          notifications={notifications}
          loading={loading}
          error={error}
          onRetry={onRetry}
          onSelect={onSelect}
        />
      </div>

      <div className="notification-dropdown__footer">
        <Link to="/notifications" onClick={onClose}>
          View all notifications
        </Link>
      </div>
    </section>
  );
}

export default NotificationDropdown;

import { formatRelativeTime } from "../../utils/notificationTime";
import {
  getNotificationConfig,
  getNotificationTarget,
} from "../../utils/notificationActions";

function NotificationItem({ notification, onSelect, compact = false }) {
  const config = getNotificationConfig(notification);
  const target = getNotificationTarget(notification);
  const isUnread = !notification.is_read;
  const timeLabel = formatRelativeTime(notification.created_at);

  return (
    <button
      type="button"
      className={`notification-item${isUnread ? " notification-item--unread" : ""}${
        compact ? " notification-item--compact" : ""
      }`}
      onClick={() => onSelect?.(notification)}
      aria-label={`${isUnread ? "Unread" : "Read"} notification: ${
        notification.title
      }${target ? ". Opens related page." : ""}`}
    >
      <span
        className={`notification-item__icon notification-item__icon--${config.tone}`}
        aria-hidden="true"
      >
        {config.icon}
      </span>

      <span className="notification-item__body">
        <span className="notification-item__header">
          <strong>{notification.title}</strong>
          {timeLabel ? (
            <time dateTime={notification.created_at}>{timeLabel}</time>
          ) : null}
        </span>
        <span className="notification-item__message">
          {notification.message}
        </span>
        <span className="notification-item__meta">
          <span>{config.label}</span>
          {target ? <span>Open related page</span> : <span>Informational</span>}
        </span>
      </span>

      <span
        className="notification-item__read-dot"
        aria-label={isUnread ? "Unread" : "Read"}
      />
    </button>
  );
}

export default NotificationItem;

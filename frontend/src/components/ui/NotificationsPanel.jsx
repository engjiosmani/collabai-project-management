import EmptyState from "./EmptyState";
import LoadingSkeleton from "./LoadingSkeleton";

function NotificationsPanel({ notifications = [], loading = false, onRefresh }) {
    if (loading) {
        return (
            <LoadingSkeleton
                variant="list"
                count={3}
                lines={2}
                label="Loading notifications"
            />
        );
    }

    if (!notifications.length) {
        return (
            <EmptyState
                compact
                icon="i"
                title="No notifications"
                description="Updates that need your attention will appear here."
                actionLabel={onRefresh ? "Refresh" : undefined}
                onAction={onRefresh}
                actionClassName="dashboard-button dashboard-button--ghost"
            />
        );
    }

    return (
        <ul className="ui-notification-list" aria-label="Notifications">
            {notifications.map((notification) => (
                <li className="ui-notification-item" key={notification.id}>
                    <strong>{notification.title}</strong>
                    {notification.description ? <p>{notification.description}</p> : null}
                </li>
            ))}
        </ul>
    );
}

export default NotificationsPanel;

import EmptyState from "../ui/EmptyState";

function formatTimestamp(value) {
    if (!value) {
        return "Just now";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

function RecentActivityList({ items }) {
    if (!items.length) {
        return (
            <EmptyState
                compact
                icon="A"
                kicker="Recent activity"
                title="No activity found"
                description="When your team updates tasks or comments, the latest events will appear here."
                className="dashboard-empty-state dashboard-empty-state--soft"
            />
        );
    }

    return (
        <ul className="dashboard-activity-list">
            {items.map((item) => (
                <li className="dashboard-activity-item" key={item.id}>
                    <div className="dashboard-activity-badge">{(item.action || "A").slice(0, 1)}</div>
                    <div className="dashboard-activity-body">
                        <div className="dashboard-activity-title-row">
                            <h4 className="dashboard-activity-title">{item.action}</h4>
                            <span className="dashboard-activity-time">{formatTimestamp(item.created_at)}</span>
                        </div>
                        <p className="dashboard-activity-meta">
                            {item.task_title ? <span>Task: {item.task_title}</span> : null}
                            {item.user_email ? <span>By: {item.user_email}</span> : null}
                        </p>
                        {item.description ? <p className="dashboard-activity-description">{item.description}</p> : null}
                    </div>
                </li>
            ))}
        </ul>
    );
}

export default RecentActivityList;


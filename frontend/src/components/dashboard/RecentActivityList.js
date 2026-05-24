import { useMemo } from "react";
import EmptyState from "../ui/EmptyState";

function formatRelativeTime(value) {
    if (!value) return "Just now";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;

    const now = Date.now();
    const diffMs = now - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 60) return "Just now";

    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;

    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;

    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 30) return `${diffDay}d ago`;

    const diffMonth = Math.floor(diffDay / 30);
    if (diffMonth < 12) return `${diffMonth}mo ago`;

    return `${Math.floor(diffMonth / 12)}y ago`;
}

function formatExactDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

function RecentActivityList({ items }) {
    const content = useMemo(() => {
        if (!items.length) {
            return (
                <div className="dashboard-activity-scroll">
                    <EmptyState
                        compact
                        icon="A"
                        kicker="Recent activity"
                        title="No recent activity yet."
                        description="Activity from projects, tasks, and workspace changes will appear here."
                        className="dashboard-empty-state dashboard-empty-state--soft"
                    />
                </div>
            );
        }

        return (
            <div className="dashboard-activity-scroll">
                <ul className="dashboard-activity-list">
                    {items.map((item) => (
                        <li className="dashboard-activity-item" key={item.id}>
                            <div className="dashboard-activity-badge">{(item.action || "A").slice(0, 1)}</div>
                            <div className="dashboard-activity-body">
                                <div className="dashboard-activity-title-row">
                                    <h4 className="dashboard-activity-title">{item.action}</h4>
                                    <span
                                        className="dashboard-activity-time"
                                        title={formatExactDate(item.created_at)}
                                    >
                                        {formatRelativeTime(item.created_at)}
                                    </span>
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
            </div>
        );
    }, [items]);

    return content;
}

export default RecentActivityList;

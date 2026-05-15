import { useContext, useRef } from "react";
import { useNavigate } from "react-router-dom";

import ActionChart from "../components/dashboard/ActionChart";
import CompletionChart from "../components/dashboard/CompletionChart";
import ErrorState from "../components/dashboard/ErrorState";
import KanbanBoard from "../components/KanbanBoard";
import RecentActivityList from "../components/dashboard/RecentActivityList";
import SkeletonCard from "../components/dashboard/SkeletonCard";
import StatCard from "../components/dashboard/StatCard";
import { AuthContext } from "../context/AuthContext";
import { DashboardProvider, useDashboard } from "../context/DashboardContext";

import "./Dashboard.css";

function DashboardSkeleton() {
    return (
        <div className="dashboard-shell">
            <aside className="dashboard-sidebar">
                <div>
                    <div className="dashboard-brand">
                        <div className="dashboard-brand-mark">C</div>
                        <div>
                            <div className="dashboard-skeleton-line dashboard-skeleton-line--title" style={{ width: "120px" }} />
                            <div className="dashboard-skeleton-line" style={{ width: "170px" }} />
                        </div>
                    </div>
                    <div className="dashboard-nav">
                        <div className="dashboard-skeleton-line" />
                        <div className="dashboard-skeleton-line" />
                        <div className="dashboard-skeleton-line" />
                    </div>
                </div>
                <div className="dashboard-sidebar-footer">
                    <div className="dashboard-skeleton-line" style={{ width: "140px" }} />
                    <div className="dashboard-skeleton-line" style={{ width: "180px" }} />
                </div>
            </aside>

            <main className="dashboard-main">
                <div className="dashboard-topbar">
                    <div>
                        <div className="dashboard-skeleton-line dashboard-skeleton-line--title" style={{ width: "260px" }} />
                        <div className="dashboard-skeleton-line" style={{ width: "420px" }} />
                    </div>
                    <div className="dashboard-actions">
                        <div className="dashboard-skeleton-line" style={{ width: "110px", height: "44px" }} />
                        <div className="dashboard-skeleton-line" style={{ width: "90px", height: "44px" }} />
                    </div>
                </div>

                <section className="dashboard-section dashboard-stat-grid">
                    <SkeletonCard lines={2} />
                    <SkeletonCard lines={2} />
                    <SkeletonCard lines={2} />
                    <SkeletonCard lines={2} />
                </section>

                <section className="dashboard-grid dashboard-section">
                    <SkeletonCard lines={5} />
                    <SkeletonCard lines={5} />
                </section>

                <section className="dashboard-panel dashboard-panel--wide">
                    <SkeletonCard lines={6} />
                </section>
            </main>
        </div>
    );
}

function DashboardScreen() {
    const { user, logout } = useContext(AuthContext);
    const navigate = useNavigate();
    const { summary, loading, refreshing, error, reload } = useDashboard();
    const kanbanRef = useRef(null);

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    const handleRefresh = () => {
        reload({ silent: true });
    };

    const handleScrollToKanban = () => {
        kanbanRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    if (loading && !summary.hasData) {
        return <DashboardSkeleton />;
    }

    if (error && !summary.hasData) {
        return (
            <div className="dashboard-main" style={{ minHeight: "100vh" }}>
                <ErrorState message={error} onRetry={handleRefresh} />
            </div>
        );
    }

    return (
        <div className="dashboard-shell">
            <aside className="dashboard-sidebar">
                <div>
                    <div className="dashboard-brand">
                        <div className="dashboard-brand-mark">C</div>
                        <div>
                            <h1 className="dashboard-brand-title">CollabAI</h1>
                            <p className="dashboard-brand-subtitle">Project intelligence hub</p>
                        </div>
                    </div>

                    <nav className="dashboard-nav" aria-label="Dashboard sections">
                        <button className="dashboard-nav-item dashboard-nav-item--active" data-cy="dashboard-nav-overview" type="button">Overview</button>
                        <button className="dashboard-nav-item" data-cy="dashboard-nav-projects" type="button">Projects</button>
                        <button className="dashboard-nav-item" data-cy="dashboard-nav-tasks" onClick={handleScrollToKanban} type="button">Tasks</button>
                        <button className="dashboard-nav-item" data-cy="dashboard-nav-activity" type="button">Activity</button>
                    </nav>
                </div>

                <div className="dashboard-sidebar-footer">
                    <p className="dashboard-sidebar-note" data-cy="dashboard-sidebar-note">
                        Connected securely over REST using JWT authentication and the shared CollabAI API client.
                    </p>
                    <button className="dashboard-button dashboard-button--ghost" data-cy="dashboard-logout" onClick={handleLogout} type="button">
                        Logout
                    </button>
                </div>
            </aside>

            <main className="dashboard-main">
                <header className="dashboard-topbar">
                    <div>
                        <h2 className="dashboard-heading" data-cy="dashboard-heading">Welcome back{user?.email ? `, ${user.email}` : ""}</h2>
                        <p className="dashboard-subheading" data-cy="dashboard-subheading">
                            Monitor project health, task completion, and recent activity from a single command center.
                        </p>
                    </div>

                    <div className="dashboard-meta" data-cy="dashboard-meta">
                        <span className="dashboard-user-pill" data-cy="dashboard-user-pill">Signed in as {user?.email || "authenticated user"}</span>
                        <span className="dashboard-status-pill">
                            {summary.lastUpdated ? `Updated ${new Intl.DateTimeFormat(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short",
                            }).format(summary.lastUpdated)}` : "Loading latest data"}
                        </span>
                        <div className="dashboard-actions">
                            <button className="dashboard-button dashboard-button--ghost" data-cy="dashboard-refresh" onClick={handleRefresh} type="button">
                                {refreshing ? "Refreshing..." : "Refresh"}
                            </button>
                            <button className="dashboard-button dashboard-button--primary" data-cy="dashboard-logout-primary" onClick={handleLogout} type="button">
                                Logout
                            </button>
                        </div>
                    </div>
                </header>

                {error ? <ErrorState message={error} onRetry={handleRefresh} /> : null}

                <section className="dashboard-section dashboard-stat-grid" data-cy="dashboard-stats" aria-label="Workspace statistics">
                    <StatCard label="Total projects" value={summary.totalProjects} hint="All projects visible to your workspace access" tone="default" />
                    <StatCard label="Total tasks" value={summary.totalTasks} hint={`${summary.completionRate}% of tasks are completed`} tone="info" />
                    <StatCard label="Completed tasks" value={summary.completedTasks} hint="Tasks with a completed status label" tone="success" />
                    <StatCard label="Pending tasks" value={summary.pendingTasks} hint="Tasks still in progress" tone="warning" />
                </section>

                <section className="dashboard-grid dashboard-section">
                    <article className="dashboard-panel">
                        <div className="dashboard-panel-header">
                            <div>
                                <h3 className="dashboard-panel-title">Task completion</h3>
                                <p className="dashboard-panel-subtitle">Completed versus pending work across all accessible projects.</p>
                            </div>
                        </div>
                        <CompletionChart completed={summary.completedTasks} pending={summary.pendingTasks} total={summary.totalTasks} />
                    </article>

                    <article className="dashboard-panel">
                        <div className="dashboard-panel-header">
                            <div>
                                <h3 className="dashboard-panel-title">Activity overview</h3>
                                <p className="dashboard-panel-subtitle">Latest actions grouped by event type.</p>
                            </div>
                        </div>
                        <ActionChart data={summary.activityByAction} />
                    </article>
                </section>

                <section className="dashboard-panel dashboard-panel--wide" data-cy="dashboard-recent-activity">
                    <div className="dashboard-panel-header">
                        <div>
                            <h3 className="dashboard-panel-title">Recent activity logs</h3>
                            <p className="dashboard-panel-subtitle">Showing the latest five events from the activity feed.</p>
                        </div>
                        <span className="dashboard-status-pill">{summary.recentActivityCount} total logs</span>
                    </div>

                    <RecentActivityList items={summary.recentActivity} />
                </section>

                <section ref={kanbanRef} className="dashboard-panel dashboard-panel--wide" data-cy="dashboard-kanban">
                    <div className="dashboard-panel-header">
                        <div>
                            <h3 className="dashboard-panel-title">Kanban task board</h3>
                            <p className="dashboard-panel-subtitle">
                                Create tasks, move them between statuses, and update them directly from the API-01 task endpoints.
                            </p>
                        </div>
                    </div>

                    <KanbanBoard />
                </section>
            </main>
        </div>
    );
}

function Dashboard() {
    return (
        <DashboardProvider>
            <DashboardScreen />
        </DashboardProvider>
    );
}

export default Dashboard;


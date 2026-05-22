import { useCallback, useContext, useEffect, useRef } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import AppSidebar from "../components/AppSidebar";
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
            <AppSidebar />

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
    const location = useLocation();
    const [searchParams, setSearchParams] = useSearchParams();
    const activityRef = useRef(null);
    const kanbanRef = useRef(null);

    const kanbanProjectFilter = searchParams.get("project") || "";

    const setKanbanProjectFilter = useCallback(
        (value) => {
            const next = value ? String(value) : "";
            const params = new URLSearchParams(searchParams);
            if (next) {
                params.set("project", next);
            } else {
                params.delete("project");
            }
            setSearchParams(params, { replace: true });
        },
        [searchParams, setSearchParams]
    );

    useEffect(() => {
        const projectId = location.state?.projectId;
        if (projectId === undefined || projectId === null) {
            return;
        }
        const params = new URLSearchParams(window.location.search);
        const next = projectId ? String(projectId) : "";
        if (next) {
            params.set("project", next);
        } else {
            params.delete("project");
        }
        const scrollTo = location.state?.scrollTo;
        setSearchParams(params, {
            replace: true,
            state: scrollTo ? { scrollTo } : {},
        });
    }, [location.key, location.state?.projectId, location.state?.scrollTo, setSearchParams]);

    const scrollToSection = useCallback((section) => {
        const targets = {
            tasks: kanbanRef,
            activity: activityRef,
        };
        targets[section]?.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, []);

    useEffect(() => {
        const target = location.state?.scrollTo;
        if (!target || !["tasks", "activity"].includes(target)) {
            return undefined;
        }
        if (loading && !summary.hasData) {
            return undefined;
        }
        const timer = window.setTimeout(() => scrollToSection(target), 150);
        return () => window.clearTimeout(timer);
    }, [location.state, loading, summary.hasData, scrollToSection]);

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    const handleRefresh = () => {
        reload({ silent: true });
    };

    const isAuthError =
        Boolean(error) &&
        (String(error).toLowerCase().includes("token") ||
            String(error).toLowerCase().includes("session"));

    if (loading && !summary.hasData) {
        return <DashboardSkeleton />;
    }

    if (error && !summary.hasData) {
        return (
            <div className="dashboard-shell">
                <AppSidebar onNavigateSection={() => {}} />

                <main className="dashboard-main">
                    <header className="dashboard-topbar">
                        <div>
                            <h2 className="dashboard-heading">Welcome back</h2>
                        </div>
                        <div className="dashboard-actions">
                            <button
                                className="dashboard-button dashboard-button--ghost"
                                type="button"
                                onClick={handleRefresh}
                            >
                                Retry
                            </button>
                            {isAuthError ? (
                                <button
                                    className="dashboard-button dashboard-button--primary"
                                    type="button"
                                    onClick={() => {
                                        logout();
                                        navigate("/login");
                                    }}
                                >
                                    Sign in again
                                </button>
                            ) : null}
                        </div>
                    </header>
                    <ErrorState message={error} />
                </main>
            </div>
        );
    }

    return (
        <div className="dashboard-shell">
            <AppSidebar onNavigateSection={scrollToSection} />

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

                {error ? <ErrorState message={error} /> : null}

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

                <section
                    ref={activityRef}
                    className="dashboard-panel dashboard-panel--wide"
                    data-cy="dashboard-recent-activity"
                >
                    <div className="dashboard-panel-header">
                        <div>
                            <h3 className="dashboard-panel-title">Recent activity logs</h3>
                            <p className="dashboard-panel-subtitle">Showing the latest five events from the activity feed.</p>
                        </div>
                        <span className="dashboard-status-pill">
                            {summary.recentActivityCount === 1
                                ? "1 total log"
                                : `${summary.recentActivityCount} total logs`}
                        </span>
                    </div>

                    <RecentActivityList items={summary.recentActivity} />
                </section>

                <section ref={kanbanRef} className="dashboard-panel dashboard-panel--wide dashboard-panel--kanban" data-cy="dashboard-kanban">
                    <KanbanBoard
                        projectFilter={kanbanProjectFilter}
                        onProjectFilterChange={setKanbanProjectFilter}
                        onTasksChanged={() => reload({ silent: true })}
                    />
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


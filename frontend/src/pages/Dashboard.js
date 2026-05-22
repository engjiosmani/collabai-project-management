import { useCallback, useContext, useEffect, useMemo, useRef } from "react";
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
import { useOrganization } from "../context/OrganizationContext";
import { useRole } from "../hooks/useRole";

import "./Dashboard.css";

const ROLE_LABELS = {
    org_admin: "Organization admin",
    workspace_admin: "Workspace admin",
    manager: "Manager",
    member: "Member",
};

function scopeCopy(role, activeOrganization) {
    const orgName = activeOrganization?.name || "your active organization";

    if (role === "org_admin") {
        return {
            subtitle: `${orgName} overview across organization-level access.`,
            projectHint: "Active projects in this organization",
            taskHint: "Tasks across projects you can administer",
            activityHint: "Latest activity across your organization scope.",
        };
    }

    if (role === "workspace_admin") {
        return {
            subtitle: `${orgName} overview across workspaces you administer.`,
            projectHint: "Projects visible through your workspace access",
            taskHint: "Tasks across projects you can administer",
            activityHint: "Latest activity across your workspace scope.",
        };
    }

    if (role === "manager") {
        return {
            subtitle: `${orgName} overview across projects you manage.`,
            projectHint: "Projects available to your manager role",
            taskHint: "Tasks you can create, assign, and update",
            activityHint: "Latest activity across managed projects.",
        };
    }

    return {
        subtitle: `${orgName} overview for your assigned work.`,
        projectHint: "Projects assigned or opened to you",
        taskHint: "Tasks assigned to you or visible through project access",
        activityHint: "Latest activity from projects you can access.",
    };
}

const DASHBOARD_PROFILES = {
    org_admin: {
        title: "Organization overview",
        eyebrow: "Governance",
        focus: "Organization health, access, and delivery across all visible work.",
        actions: [
            { label: "Invite member", target: "/organizations", tone: "primary" },
            { label: "Manage organization", target: "/organizations" },
            { label: "Review projects", target: "/projects" },
            { label: "Open task board", section: "tasks" },
        ],
    },
    workspace_admin: {
        title: "Workspace overview",
        eyebrow: "Workspace operations",
        focus: "Workspace settings, members, and delivery across your administered workspaces.",
        actions: [
            { label: "Workspace members", target: "/organizations", tone: "primary" },
            { label: "Workspace settings", target: "/organizations" },
            { label: "Review projects", target: "/projects" },
            { label: "Open task board", section: "tasks" },
        ],
    },
    manager: {
        title: "Delivery overview",
        eyebrow: "Manager cockpit",
        focus: "Project execution, task assignment, and progress across work you manage.",
        actions: [
            { label: "Create task", section: "tasks", tone: "primary" },
            { label: "Review projects", target: "/projects" },
            { label: "Check activity", section: "activity" },
        ],
    },
    member: {
        title: "My work",
        eyebrow: "Assigned work",
        focus: "Tasks and project activity assigned or opened to you.",
        actions: [
            { label: "Open my tasks", section: "tasks", tone: "primary" },
            { label: "Review activity", section: "activity" },
            { label: "View projects", target: "/projects" },
        ],
    },
};

function getDashboardProfile(role) {
    return DASHBOARD_PROFILES[role] || DASHBOARD_PROFILES.member;
}

function RoleCommandPanel({ profile, roleLabel, onAction }) {
    return (
        <section className="dashboard-role-panel dashboard-section" data-cy="dashboard-role-panel">
            <div className="dashboard-role-panel__main">
                <p className="dashboard-empty-kicker">{profile.eyebrow}</p>
                <h3>{profile.title}</h3>
                <p>{profile.focus}</p>
            </div>
            <div className="dashboard-role-panel__side">
                <span className="dashboard-status-pill">{roleLabel}</span>
                <div className="dashboard-role-actions">
                    {profile.actions.map((action) => (
                        <button
                            key={`${action.label}-${action.target || action.section}`}
                            className={`dashboard-button ${
                                action.tone === "primary"
                                    ? "dashboard-button--primary"
                                    : "dashboard-button--ghost"
                            }`}
                            type="button"
                            onClick={() => onAction(action)}
                        >
                            {action.label}
                        </button>
                    ))}
                </div>
            </div>
        </section>
    );
}

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
    const { activeOrganization } = useOrganization();
    const { role } = useRole();
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

    const roleLabel = ROLE_LABELS[role] || "Member";
    const copy = scopeCopy(role, activeOrganization);
    const profile = getDashboardProfile(role);
    const isMemberView = role === "member" || !role;

    const handleRoleAction = useCallback(
        (action) => {
            if (action.target) {
                navigate(action.target);
                return;
            }
            if (action.section) {
                scrollToSection(action.section);
            }
        },
        [navigate, scrollToSection]
    );

    const statCards = useMemo(() => {
        if (isMemberView) {
            return [
                { label: "My projects", value: summary.totalProjects, hint: copy.projectHint, tone: "default" },
                { label: "My tasks", value: summary.totalTasks, hint: copy.taskHint, tone: "info" },
                { label: "Done", value: summary.completedTasks, hint: `${summary.completionRate}% completed`, tone: "success" },
                { label: "Open", value: summary.pendingTasks, hint: "Tasks still waiting on progress", tone: "warning" },
            ];
        }

        return [
            { label: "Projects", value: summary.totalProjects, hint: copy.projectHint, tone: "default" },
            { label: "Total tasks", value: summary.totalTasks, hint: copy.taskHint, tone: "info" },
            { label: "Completed tasks", value: summary.completedTasks, hint: "Tasks with a completed status label", tone: "success" },
            { label: "Pending tasks", value: summary.pendingTasks, hint: "Tasks still in progress", tone: "warning" },
        ];
    }, [copy.projectHint, copy.taskHint, isMemberView, summary.completedTasks, summary.completionRate, summary.pendingTasks, summary.totalProjects, summary.totalTasks]);

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
                        <h2 className="dashboard-heading" data-cy="dashboard-heading">{profile.title}</h2>
                        <p className="dashboard-subheading" data-cy="dashboard-subheading">
                            {copy.subtitle}
                        </p>
                    </div>

                    <div className="dashboard-meta" data-cy="dashboard-meta">
                        <span className="dashboard-user-pill" data-cy="dashboard-user-pill">Signed in as {user?.email || "authenticated user"}</span>
                        <span className="dashboard-status-pill">{roleLabel}</span>
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

                <RoleCommandPanel
                    profile={profile}
                    roleLabel={roleLabel}
                    onAction={handleRoleAction}
                />

                <section className="dashboard-section dashboard-stat-grid" data-cy="dashboard-stats" aria-label="Role statistics">
                    {statCards.map((card) => (
                        <StatCard
                            key={card.label}
                            label={card.label}
                            value={card.value}
                            hint={card.hint}
                            tone={card.tone}
                        />
                    ))}
                </section>

                {!isMemberView ? (
                <section className="dashboard-grid dashboard-section">
                    <article className="dashboard-panel">
                        <div className="dashboard-panel-header">
                            <div>
                                <h3 className="dashboard-panel-title">Task completion</h3>
                                <p className="dashboard-panel-subtitle">Completed versus pending work in your current access scope.</p>
                            </div>
                        </div>
                        <CompletionChart completed={summary.completedTasks} pending={summary.pendingTasks} total={summary.totalTasks} />
                    </article>

                    <article className="dashboard-panel">
                        <div className="dashboard-panel-header">
                            <div>
                                <h3 className="dashboard-panel-title">Activity overview</h3>
                                <p className="dashboard-panel-subtitle">Latest actions grouped by event type in your current access scope.</p>
                            </div>
                        </div>
                        <ActionChart data={summary.activityByAction} />
                    </article>
                </section>
                ) : null}

                {isMemberView ? (
                    <section ref={kanbanRef} className="dashboard-panel dashboard-panel--wide dashboard-panel--kanban" data-cy="dashboard-kanban">
                        <KanbanBoard
                            projectFilter={kanbanProjectFilter}
                            onProjectFilterChange={setKanbanProjectFilter}
                            onTasksChanged={() => reload({ silent: true })}
                        />
                    </section>
                ) : null}

                <section
                    ref={activityRef}
                    className="dashboard-panel dashboard-panel--wide"
                    data-cy="dashboard-recent-activity"
                >
                    <div className="dashboard-panel-header">
                        <div>
                            <h3 className="dashboard-panel-title">Recent activity logs</h3>
                            <p className="dashboard-panel-subtitle">{copy.activityHint}</p>
                        </div>
                        <span className="dashboard-status-pill">
                            {summary.recentActivityCount === 1
                                ? "1 total log"
                                : `${summary.recentActivityCount} total logs`}
                        </span>
                    </div>

                    <RecentActivityList items={summary.recentActivity} />
                </section>

                {!isMemberView ? (
                <section ref={kanbanRef} className="dashboard-panel dashboard-panel--wide dashboard-panel--kanban" data-cy="dashboard-kanban">
                    <KanbanBoard
                        projectFilter={kanbanProjectFilter}
                        onProjectFilterChange={setKanbanProjectFilter}
                        onTasksChanged={() => reload({ silent: true })}
                    />
                </section>
                ) : null}
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


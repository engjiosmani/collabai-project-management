import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import API from "../api/api";
import { AuthContext } from "./AuthContext";

export const DashboardContext = createContext(null);

const COMPLETED_STATUS_HINTS = [
    "done",
    "completed",
    "complete",
    "closed",
    "resolved",
    "finished",
    "deployed",
];

const isCompletedStatus = (statusName) => {
    if (!statusName) {
        return false;
    }

    const normalized = String(statusName).toLowerCase();
    return COMPLETED_STATUS_HINTS.some((hint) => normalized.includes(hint));
};

const buildActionSummary = (activityLogs) => {
    const summary = new Map();

    activityLogs.forEach((entry) => {
        const label = entry.action || "UNKNOWN";
        summary.set(label, (summary.get(label) || 0) + 1);
    });

    return Array.from(summary.entries()).map(([name, value]) => ({
        name,
        value,
    }));
};

// The dashboard summary endpoint returns the aggregated counts and
// recent activity in a single small response. This avoids fetching
// all projects/tasks paginated client-side which is not scalable.
const fetchDashboardSummary = async ({ signal } = {}) => {
    const response = await API.get("/dashboard/summary/", { signal });
    return response.data || {};
};

export const DashboardProvider = ({ children }) => {
    const { accessToken } = useContext(AuthContext);
    const [projects, setProjects] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [activityLogs, setActivityLogs] = useState([]);
    const [loading, setLoading] = useState(Boolean(accessToken));
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(null);
    const [serverCounts, setServerCounts] = useState(null);

    const loadDashboard = useCallback(
        async ({ signal, silent = false } = {}) => {
            if (!accessToken) {
                setProjects([]);
                setTasks([]);
                setActivityLogs([]);
                setLoading(false);
                setRefreshing(false);
                return;
            }

            if (silent) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }

            setError("");

            try {
                const payload = await fetchDashboardSummary({ signal });

                // payload shape:
                // {
                //   total_projects, total_tasks, completed_tasks, pending_tasks,
                //   recent_activity: [...], activity_by_action: [...]
                // }

                setProjects([]); // we don't fetch full lists here
                setTasks([]);
                setActivityLogs(payload.recent_activity || []);
                setServerCounts({
                    total_projects: payload.total_projects ?? 0,
                    total_tasks: payload.total_tasks ?? 0,
                    completed_tasks: payload.completed_tasks ?? 0,
                    pending_tasks: payload.pending_tasks ?? 0,
                    activity_by_action: payload.activity_by_action ?? null,
                });
                setLastUpdated(new Date());
            } catch (requestError) {
                if (signal?.aborted || requestError?.code === "ERR_CANCELED") {
                    return;
                }

                const detail =
                    requestError.response?.data?.detail ||
                    requestError.response?.data?.message ||
                    requestError.message ||
                    "Unable to load dashboard data.";

                const isAuthError =
                    requestError.response?.status === 401 ||
                    String(detail).toLowerCase().includes("token");

                setError(
                    isAuthError
                        ? "Your session expired. Redirecting to sign in…"
                        : detail
                );
            } finally {
                if (!signal?.aborted) {
                    setLoading(false);
                    setRefreshing(false);
                }
            }
        },
        [accessToken]
    );

    useEffect(() => {
        const controller = new AbortController();
        loadDashboard({ signal: controller.signal });
        return () => controller.abort();
    }, [loadDashboard]);

    const summary = useMemo(() => {
        // If the server supplied pre-aggregated counts, prefer them.
        // Otherwise fall back to client-side computation (rare path).
        const totalProjects = serverCounts ? serverCounts.total_projects : projects.length;
        const totalTasks = serverCounts ? serverCounts.total_tasks : tasks.length;
        const completedTasks = serverCounts ? serverCounts.completed_tasks : tasks.filter((t) => isCompletedStatus(t.status_name)).length;
        const pendingTasks = serverCounts ? serverCounts.pending_tasks : Math.max(tasks.length - completedTasks, 0);

        const recentActivity = activityLogs.slice(0, 5);

        return {
            totalProjects,
            totalTasks,
            completedTasks,
            pendingTasks,
            completionRate: 0,
            recentActivity,
            recentActivityCount: activityLogs.length,
            activityByAction: serverCounts && serverCounts.activity_by_action ? serverCounts.activity_by_action : buildActionSummary(activityLogs),
            hasData: activityLogs.length > 0,
            lastUpdated,
        };
    }, [activityLogs, lastUpdated, serverCounts, projects.length, tasks]);

    const value = useMemo(
        () => ({
            projects,
            tasks,
            activityLogs,
            summary,
            loading,
            refreshing,
            error,
            reload: loadDashboard,
        }),
        [activityLogs, error, loadDashboard, loading, projects, refreshing, summary, tasks]
    );

    return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
};

export const useDashboard = () => {
    const context = useContext(DashboardContext);

    if (!context) {
        throw new Error("useDashboard must be used within a DashboardProvider");
    }

    return context;
};





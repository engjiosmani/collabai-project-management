import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";

import AppSidebar from "../components/AppSidebar";
import KanbanBoard from "../components/KanbanBoard";
import { useOrganization } from "../context/OrganizationContext";

import "./Dashboard.css";
import "./Tasks.css";

function Tasks() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [refreshKey, setRefreshKey] = useState(0);
    const { activeOrganization } = useOrganization();
    const projectFilter = searchParams.get("project") || "";

    const setProjectFilter = useCallback(
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

    return (
        <div className="dashboard-shell tasks-shell">
            <AppSidebar />

            <main className="dashboard-main tasks-main">
                <header className="dashboard-topbar tasks-topbar">
                    <div>
                        <p className="tasks-eyebrow">Delivery board</p>
                        <h2 className="dashboard-heading" data-cy="tasks-heading">Task board</h2>
                        <p className="dashboard-subheading">
                            Drag tasks between columns and keep project work moving in one focused view.
                        </p>
                    </div>

                    <div className="dashboard-meta">
                        <span className="dashboard-status-pill">
                            {activeOrganization?.name || "Active organization"}
                        </span>
                        <button
                            className="dashboard-button dashboard-button--ghost"
                            type="button"
                            onClick={() => setRefreshKey((value) => value + 1)}
                        >
                            Refresh
                        </button>
                    </div>
                </header>

                <section className="tasks-board-surface" data-cy="tasks-kanban">
                    <KanbanBoard
                        key={refreshKey}
                        projectFilter={projectFilter}
                        onProjectFilterChange={setProjectFilter}
                    />
                </section>
            </main>
        </div>
    );
}

export default Tasks;

import { useCallback, useEffect, useState } from "react";

import API, { getApiErrorMessage } from "../api/api";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

import "./ProjectsPanel.css";

export default function ProjectsPanel({ onSelectProject, selectedProjectId, layout = "dashboard" }) {
    const isPageLayout = layout === "page";
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await API.get("/projects/");
            const list = Array.isArray(res.data) ? res.data : res.data.results ?? [];
            setProjects(list);
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not load projects."));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    return (
        <section
            className={`dashboard-panel dashboard-panel--wide projects-panel${isPageLayout ? " projects-panel--page" : ""}`}
            data-cy={isPageLayout ? "projects-page-list" : "dashboard-projects"}
            aria-label="Your projects"
        >
            <div className="dashboard-panel-header">
                {!isPageLayout ? (
                    <div>
                        <h3 className="dashboard-panel-title">Your projects</h3>
                        <p className="dashboard-panel-subtitle">
                            Select a project to filter the Kanban board below, or view all tasks.
                        </p>
                    </div>
                ) : null}
                <button
                    type="button"
                    className="dashboard-button dashboard-button--ghost"
                    onClick={load}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Refresh list"}
                </button>
            </div>

            {error ? (
                <div className="projects-panel-error" role="alert">
                    <p>{error}</p>
                    <button type="button" className="dashboard-button dashboard-button--primary" onClick={load}>
                        Retry
                    </button>
                </div>
            ) : null}

            {loading && !error ? (
                <p className="projects-panel-muted">Loading projects…</p>
            ) : null}

            {!loading && !error && projects.length === 0 ? (
                <p className="projects-panel-muted">
                    No projects yet. Use Task Generator to create one, or add a project via the API.
                </p>
            ) : null}

            {!loading && !error && projects.length > 0 ? (
                <ul className="projects-panel-list">
                    {projects.map((project) => {
                        const isSelected = String(selectedProjectId) === String(project.id);
                        const workspaceLabel =
                            project.organization_name || project.workspace_name
                                ? formatWorkspaceLabel({
                                      name: project.workspace_name || project.name,
                                      organization_name: project.organization_name,
                                  })
                                : null;
                        return (
                            <li key={project.id}>
                                <article
                                    className={`projects-panel-card${isSelected ? " projects-panel-card--active" : ""}`}
                                >
                                    <div className="projects-panel-card-head">
                                        <h4 className="projects-panel-card-title">{project.name}</h4>
                                        {project.is_active === false ? (
                                            <span className="projects-panel-badge projects-panel-badge--inactive">
                                                Inactive
                                            </span>
                                        ) : (
                                            <span className="projects-panel-badge">Active</span>
                                        )}
                                    </div>
                                    {workspaceLabel && workspaceLabel !== project.name ? (
                                        <p className="projects-panel-card-meta">{workspaceLabel}</p>
                                    ) : null}
                                    {project.description ? (
                                        <p className="projects-panel-card-desc">
                                            {project.description.length > 160
                                                ? `${project.description.slice(0, 160)}…`
                                                : project.description}
                                        </p>
                                    ) : (
                                        <p className="projects-panel-card-desc projects-panel-card-desc--empty">
                                            No description
                                        </p>
                                    )}
                                    {(project.start_date || project.due_date) && (
                                        <p className="projects-panel-card-dates">
                                            {project.start_date ? `Start: ${project.start_date}` : ""}
                                            {project.start_date && project.due_date ? " · " : ""}
                                            {project.due_date ? `Due: ${project.due_date}` : ""}
                                        </p>
                                    )}
                                    <div className="projects-panel-card-actions">
                                        <button
                                            type="button"
                                            className="dashboard-button dashboard-button--primary"
                                            onClick={() => onSelectProject?.(project.id)}
                                        >
                                            {isSelected ? "Showing tasks" : isPageLayout ? "Open tasks" : "View tasks"}
                                        </button>
                                        {isSelected ? (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--ghost"
                                                onClick={() => onSelectProject?.("")}
                                            >
                                                Show all tasks
                                            </button>
                                        ) : null}
                                    </div>
                                </article>
                            </li>
                        );
                    })}
                </ul>
            ) : null}
        </section>
    );
}

import { useCallback, useEffect, useState } from "react";

import API, { getApiErrorMessage } from "../api/api";
import { useOrganization } from "../context/OrganizationContext";
import { useRole } from "../hooks/useRole";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

import "./ProjectsPanel.css";

const emptyForm = {
    name: "",
    description: "",
    start_date: "",
    due_date: "",
};

export default function ProjectsPanel({ onSelectProject, selectedProjectId, layout = "dashboard" }) {
    const isPageLayout = layout === "page";
    const { activeOrganization } = useOrganization();
    const { isOrgAdmin, isManagerOrAbove } = useRole();
    const canManageProjects = isManagerOrAbove();
    const canArchiveProjects = isOrgAdmin();

    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [editingProject, setEditingProject] = useState(null);
    const [form, setForm] = useState(emptyForm);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = activeOrganization?.id ? { organization: activeOrganization.id } : {};
            const res = await API.get("/projects/", { params });
            const list = Array.isArray(res.data) ? res.data : res.data.results ?? [];
            setProjects(list);
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not load projects."));
        } finally {
            setLoading(false);
        }
    }, [activeOrganization?.id]);

    useEffect(() => {
        load();
    }, [load]);

    const resetForm = () => {
        setEditingProject(null);
        setForm(emptyForm);
    };

    const startEdit = (project) => {
        setEditingProject(project);
        setForm({
            name: project.name || "",
            description: project.description || "",
            start_date: project.start_date || "",
            due_date: project.due_date || "",
        });
    };

    const saveProject = async (event) => {
        event.preventDefault();
        if (!canManageProjects) return;

        if (!activeOrganization?.id) {
            setError("Select an organization before creating a project.");
            return;
        }

        if (!form.name.trim()) {
            setError("Project name is required.");
            return;
        }

        setSaving(true);
        setError(null);

        const payload = {
            organization: activeOrganization.id,
            name: form.name.trim(),
            description: form.description.trim(),
            start_date: form.start_date || null,
            due_date: form.due_date || null,
        };

        try {
            if (editingProject) {
                await API.patch(`/projects/${editingProject.id}/`, payload);
            } else {
                await API.post("/projects/", payload);
            }
            resetForm();
            await load();
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not save project."));
        } finally {
            setSaving(false);
        }
    };

    const archiveProject = async (project) => {
        if (!canArchiveProjects) return;
        if (!window.confirm(`Archive project "${project.name}"?`)) return;

        setError(null);
        try {
            await API.delete(`/projects/${project.id}/`);
            if (String(selectedProjectId) === String(project.id)) {
                onSelectProject?.("");
            }
            await load();
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not archive project."));
        }
    };

    return (
        <section
            className={`dashboard-panel dashboard-panel--wide projects-panel${isPageLayout ? " projects-panel--page" : ""}`}
            data-cy={isPageLayout ? "projects-page-list" : "dashboard-projects"}
            aria-label="Your projects"
        >
            <div className="dashboard-panel-header">
                {!isPageLayout ? (
                    <div>
                        <h3 className="dashboard-panel-title">Projects</h3>
                        <p className="dashboard-panel-subtitle">
                            Browse projects in your current organization and open their tasks.
                        </p>
                    </div>
                ) : null}

                <div className="projects-panel-header-actions">
                    {canManageProjects ? (
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--primary"
                            onClick={resetForm}
                        >
                            New project
                        </button>
                    ) : null}
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--ghost"
                        onClick={load}
                        disabled={loading}
                    >
                        {loading ? "Loading..." : "Refresh"}
                    </button>
                </div>
            </div>

            {canManageProjects ? (
                <form className="projects-panel-form" onSubmit={saveProject}>
                    <div className="projects-panel-form-grid">
                        <label>
                            <span>Name</span>
                            <input
                                value={form.name}
                                onChange={(event) =>
                                    setForm((current) => ({ ...current, name: event.target.value }))
                                }
                                placeholder="Project name"
                            />
                        </label>
                        <label>
                            <span>Start</span>
                            <input
                                type="date"
                                value={form.start_date}
                                onChange={(event) =>
                                    setForm((current) => ({ ...current, start_date: event.target.value }))
                                }
                            />
                        </label>
                        <label>
                            <span>Due</span>
                            <input
                                type="date"
                                value={form.due_date}
                                onChange={(event) =>
                                    setForm((current) => ({ ...current, due_date: event.target.value }))
                                }
                            />
                        </label>
                    </div>
                    <label>
                        <span>Description</span>
                        <textarea
                            value={form.description}
                            onChange={(event) =>
                                setForm((current) => ({ ...current, description: event.target.value }))
                            }
                            placeholder="Short project summary"
                            rows={3}
                        />
                    </label>
                    <div className="projects-panel-form-actions">
                        <button
                            type="submit"
                            className="dashboard-button dashboard-button--primary"
                            disabled={saving}
                        >
                            {saving ? "Saving..." : editingProject ? "Save project" : "Create project"}
                        </button>
                        {editingProject ? (
                            <button
                                type="button"
                                className="dashboard-button dashboard-button--ghost"
                                onClick={resetForm}
                            >
                                Cancel
                            </button>
                        ) : null}
                    </div>
                </form>
            ) : null}

            {error ? (
                <div className="projects-panel-error" role="alert">
                    <p>{error}</p>
                    <button type="button" className="dashboard-button dashboard-button--primary" onClick={load}>
                        Retry
                    </button>
                </div>
            ) : null}

            {loading && !error ? (
                <p className="projects-panel-muted">Loading projects...</p>
            ) : null}

            {!loading && !error && projects.length === 0 ? (
                <p className="projects-panel-muted">
                    {canManageProjects
                        ? "No projects yet. Create the first project for this organization."
                        : "No projects are assigned or visible to you yet."}
                </p>
            ) : null}

            {!loading && !error && projects.length > 0 ? (
                <ul className="projects-panel-list">
                    {projects.map((project) => {
                        const isSelected = String(selectedProjectId) === String(project.id);
                        const workspaceLabel = project.workspace_name
                            ? formatWorkspaceLabel({ name: project.workspace_name })
                            : null;

                        return (
                            <li key={project.id}>
                                <article className={`projects-panel-card${isSelected ? " projects-panel-card--active" : ""}`}>
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
                                                ? `${project.description.slice(0, 160)}...`
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
                                            {project.start_date && project.due_date ? " - " : ""}
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
                                        {canManageProjects ? (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--ghost"
                                                onClick={() => startEdit(project)}
                                            >
                                                Edit
                                            </button>
                                        ) : null}
                                        {isSelected ? (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--ghost"
                                                onClick={() => onSelectProject?.("")}
                                            >
                                                Show all tasks
                                            </button>
                                        ) : null}
                                        {canArchiveProjects ? (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--danger"
                                                onClick={() => archiveProject(project)}
                                            >
                                                Archive
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

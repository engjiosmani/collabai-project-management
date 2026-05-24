import { useCallback, useContext, useEffect, useState } from "react";
import API, { getApiErrorMessage } from "../api/api";
import { deleteProject, fetchProjectsPaginated } from "../api/projects";
import { AuthContext } from "../context/AuthContext";
import EmptyState from "./ui/EmptyState";
import LoadingSkeleton from "./ui/LoadingSkeleton";
import ProjectFormModal from "./ProjectFormModal";
import "./ProjectsPanel.css";

const PAGE_SIZE = 12;
const SORT_OPTIONS = [
    { value: "-created_at", label: "Newest first" },
    { value: "created_at", label: "Oldest first" },
    { value: "name", label: "Name A–Z" },
    { value: "-name", label: "Name Z–A" },
    { value: "due_date", label: "Due date ↑" },
    { value: "-due_date", label: "Due date ↓" },
];

export default function ProjectsPanel({
    onSelectProject,
    selectedProjectId,
    layout = "dashboard",
}) {
    const { isAdminOfOrg, isManagerOrAdminOfOrg } = useContext(AuthContext);
    const isPageLayout = layout === "page";

    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState(null);

    const [total, setTotal] = useState(0);
    const [nextPageUrl, setNextPageUrl] = useState(null);

    // Filters / search / sort
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [orgFilter, setOrgFilter] = useState("");
    const [workspaceFilter, setWorkspaceFilter] = useState("");
    const [workspaces, setWorkspaces] = useState([]);
    const [sortBy, setSortBy] = useState("-created_at");

    // Organizations for filter dropdown
    const [organizations, setOrganizations] = useState([]);

    // Modals
    const [showCreate, setShowCreate] = useState(false);
    const [editProject, setEditProject] = useState(null);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState(null);
    const [refreshToken, setRefreshToken] = useState(0);

    // ── Load organizations ───────────────────────────────────────────────────

    useEffect(() => {
        API.get("/organizations/")
            .then((res) => {
                const list = Array.isArray(res.data)
                    ? res.data
                    : res.data.results ?? [];
                setOrganizations(list);
            })
            .catch(() => {});
    }, []);

    // ── Load projects ────────────────────────────────────────────────────────

    const loadProjects = useCallback(
        async ({ reset = true, nextUrl = null } = {}) => {
            if (reset) {
                setLoading(true);
            } else {
                setLoadingMore(true);
            }
            setError(null);

            const params = reset
                ? {
                      page_size: PAGE_SIZE,
                      ordering: sortBy,
                      ...(debouncedSearch.trim()
                          ? { search: debouncedSearch.trim() }
                          : {}),
                      ...(orgFilter ? { organization: orgFilter } : {}),
                      ...(workspaceFilter ? { workspace: workspaceFilter } : {}),
                  }
                : null;

            try {
                const payload = nextUrl
                    ? (await API.get(nextUrl)).data
                    : await fetchProjectsPaginated(params);
                const results = Array.isArray(payload) ? payload : payload.results ?? [];
                const count = typeof payload?.count === "number" ? payload.count : null;

                setProjects((prev) => (reset ? results : [...prev, ...results]));
                setTotal((prev) => {
                    if (count !== null) return count;
                    return reset ? results.length : prev + results.length;
                });
                setNextPageUrl(payload?.next || null);
            } catch (err) {
                setError(getApiErrorMessage(err, "Could not load projects."));
                if (reset) {
                    setProjects([]);
                    setTotal(0);
                    setNextPageUrl(null);
                }
            } finally {
                setLoading(false);
                setLoadingMore(false);
            }
        },
        [debouncedSearch, orgFilter, workspaceFilter, sortBy]
    );

    useEffect(() => {
        loadProjects({ reset: true });
    }, [loadProjects, refreshToken]);

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(search);
        }, 300);

        return () => clearTimeout(timer);
    }, [search]);

    const handleSearchChange = (e) => {
        setSearch(e.target.value);
    };

    // ── Org filter ───────────────────────────────────────────────────────────

    // ── Load workspaces when org filter changes ──────────────────────────

    useEffect(() => {
        if (!orgFilter) {
            setWorkspaces([]);
            setWorkspaceFilter("");
            return;
        }
        API.get(`/organizations/${orgFilter}/workspaces/`)
            .then((res) => {
                const list = Array.isArray(res.data) ? res.data : res.data.results ?? [];
                setWorkspaces(list);
            })
            .catch(() => setWorkspaces([]));
    }, [orgFilter]);

    const handleOrgFilterChange = (e) => {
        setOrgFilter(e.target.value);
        setWorkspaceFilter("");
    };

    const handleWorkspaceFilterChange = (e) => {
        setWorkspaceFilter(e.target.value);
    };

    // ── Sort ─────────────────────────────────────────────────────────────────

    const handleSortChange = (e) => {
        setSortBy(e.target.value);
    };

    // ── Load more ────────────────────────────────────────────────────────────

    const handleLoadMore = () => {
        if (!nextPageUrl) return;
        loadProjects({ reset: false, nextUrl: nextPageUrl });
    };

    // ── Create / Edit saved callback ─────────────────────────────────────────

    const handleSaved = () => {
        setRefreshToken((current) => current + 1);
        setEditProject(null);
        setShowCreate(false);
    };

    // ── Delete ───────────────────────────────────────────────────────────────

    const handleDeleteConfirm = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        setDeleteError(null);
        try {
            await deleteProject(deleteTarget.id);
            setDeleteTarget(null);
            setRefreshToken((current) => current + 1);
        } catch (err) {
            setDeleteError(getApiErrorMessage(err, "Could not delete project."));
        } finally {
            setDeleting(false);
        }
    };

    const hasMore = Boolean(nextPageUrl);

    // ── Dashboard layout (compact, project selector only) ────────────────────

    if (!isPageLayout) {
        return (
            <section
                className="dashboard-panel dashboard-panel--wide projects-panel"
                data-cy="dashboard-projects"
                aria-label="Your projects"
            >
                <div className="dashboard-panel-header">
                    <div>
                        <h3 className="dashboard-panel-title">Your projects</h3>
                        <p className="dashboard-panel-subtitle">
                            Select a project to filter tasks.
                        </p>
                    </div>
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--ghost"
                        onClick={() => loadProjects({ reset: true })}
                        disabled={loading}
                    >
                        {loading ? "Refreshing" : "Refresh"}
                    </button>
                </div>

                {error && <p className="projects-panel-error">{error}</p>}
                {loading && (
                    <LoadingSkeleton
                        variant="list"
                        count={2}
                        lines={2}
                        label="Loading projects"
                    />
                )}
                {!loading && projects.length === 0 && (
                    <EmptyState
                        compact
                        icon="P"
                        title="No projects yet"
                        description="Create a project to start organizing tasks and team activity."
                    />
                )}
                {!loading && projects.length > 0 && (
                    <ul className="projects-panel-list">
                        {projects.map((p) => {
                            const isSelected =
                                String(selectedProjectId) === String(p.id);
                            return (
                                <li key={p.id}>
                                    <article
                                        className={`projects-panel-card${
                                            isSelected
                                                ? " projects-panel-card--active"
                                                : ""
                                        }`}
                                    >
                                        <div className="projects-panel-card-head">
                                            <h4 className="projects-panel-card-title">
                                                {p.name}
                                            </h4>
                                            <span
                                                className={`projects-panel-badge${
                                                    p.is_active === false
                                                        ? " projects-panel-badge--inactive"
                                                        : ""
                                                }`}
                                            >
                                                {p.is_active === false
                                                    ? "Inactive"
                                                    : "Active"}
                                            </span>
                                        </div>
                                        {p.organization_name && (
                                            <p className="projects-panel-card-meta">
                                                {p.organization_name}
                                                {p.workspace_name
                                                    ? ` · ${p.workspace_name}`
                                                    : ""}
                                            </p>
                                        )}
                                        <div className="projects-panel-card-actions">
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--primary"
                                                onClick={() =>
                                                    onSelectProject?.(
                                                        isSelected ? "" : p.id
                                                    )
                                                }
                                            >
                                                {isSelected
                                                    ? "Clear filter"
                                                    : "View tasks"}
                                            </button>
                                        </div>
                                    </article>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </section>
        );
    }

    // ── Page layout (full CRUD + search + filter + sort) ─────────────────────

    return (
        <>
            <section
                className="projects-panel projects-panel--page"
                data-cy="projects-page-list"
                aria-label="Projects"
            >
                {/* Toolbar */}
                <div className="pp-toolbar">
                    <div className="pp-toolbar-left">
                        <div className="pp-search-wrap">
                            <input
                                type="search"
                                className="pp-search-input"
                                placeholder="Search projects…"
                                value={search}
                                onChange={handleSearchChange}
                                aria-label="Search projects"
                            />
                        </div>

                        {organizations.length > 0 && (
                            <select
                                className="pp-filter-select"
                                value={orgFilter}
                                onChange={handleOrgFilterChange}
                                aria-label="Filter by organization"
                            >
                                <option value="">All organizations</option>
                                {organizations.map((org) => (
                                    <option key={org.id} value={org.id}>
                                        {org.name}
                                    </option>
                                ))}
                            </select>
                        )}

                        {orgFilter && workspaces.length > 0 && (
                            <select
                                className="pp-filter-select"
                                value={workspaceFilter}
                                onChange={handleWorkspaceFilterChange}
                                aria-label="Filter by workspace"
                            >
                                <option value="">All workspaces</option>
                                {workspaces.map((ws) => (
                                    <option key={ws.id} value={ws.id}>
                                        {ws.name}
                                    </option>
                                ))}
                            </select>
                        )}

                        <select
                            className="pp-filter-select"
                            value={sortBy}
                            onChange={handleSortChange}
                            aria-label="Sort projects"
                        >
                            {SORT_OPTIONS.map((o) => (
                                <option key={o.value} value={o.value}>
                                    {o.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <button
                        type="button"
                        className="dashboard-button dashboard-button--primary"
                        onClick={() => setShowCreate(true)}
                        data-cy="create-project-btn"
                    >
                        + New Project
                    </button>
                </div>

                {/* Result count */}
                {!loading && !error && (
                    <p className="pp-count">
                        {total === 0
                            ? "No projects found"
                            : `${total} project${total !== 1 ? "s" : ""}`}
                        {search ? ` matching "${search}"` : ""}
                    </p>
                )}

                {/* Error */}
                {error && (
                    <div className="projects-panel-error" role="alert">
                        <p>{error}</p>
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--primary"
                            onClick={() => loadProjects({ reset: true })}
                        >
                            Retry
                        </button>
                    </div>
                )}

                {/* Loading skeleton */}
                {loading && (
                    <LoadingSkeleton
                        className="pp-grid"
                        variant="card"
                        count={6}
                        lines={4}
                        label="Loading projects"
                    />
                )}

                {/* Empty state */}
                {!loading && !error && projects.length === 0 && (
                    <EmptyState
                        icon="P"
                        title={
                            search || orgFilter
                                ? "No projects match your search"
                                : "No projects yet"
                        }
                        description={
                            search || orgFilter
                                ? "Try a different search term or clear the active filters."
                                : "Create your first project to group tasks, members, dates, and delivery context."
                        }
                        actionLabel={
                            search || orgFilter
                                ? "Clear filters"
                                : "Create your first project"
                        }
                        actionClassName={
                            search || orgFilter
                                ? "dashboard-button dashboard-button--ghost"
                                : "dashboard-button dashboard-button--primary"
                        }
                        onAction={() => {
                            if (search || orgFilter) {
                                setSearch("");
                                setOrgFilter("");
                                setDebouncedSearch("");
                                setRefreshToken((current) => current + 1);
                                return;
                            }
                            setShowCreate(true);
                        }}
                    />
                )}

                {/* Project cards */}
                {!loading && projects.length > 0 && (
                    <div className="pp-grid">
                        {projects.map((project) => {
                            const organizationId = project.organization?.id ?? project.organization;
                            const canEdit = isManagerOrAdminOfOrg(
                                organizationId
                            );
                            const canDelete = isAdminOfOrg(organizationId);

                            return (
                                <article
                                    key={project.id}
                                    className="projects-panel-card"
                                    data-cy={`project-card-${project.id}`}
                                >
                                    <div className="projects-panel-card-head">
                                        <h4 className="projects-panel-card-title">
                                            {project.name}
                                        </h4>
                                        <span
                                            className={`projects-panel-badge${
                                                project.is_active === false
                                                    ? " projects-panel-badge--inactive"
                                                    : ""
                                            }`}
                                        >
                                            {project.is_active === false
                                                ? "Inactive"
                                                : "Active"}
                                        </span>
                                    </div>

                                    {project.organization_name && (
                                        <p className="projects-panel-card-meta">
                                            {project.organization_name}
                                            {project.workspace_name
                                                ? ` · ${project.workspace_name}`
                                                : ""}
                                        </p>
                                    )}

                                    <p
                                        className={`projects-panel-card-desc${
                                            !project.description
                                                ? " projects-panel-card-desc--empty"
                                                : ""
                                        }`}
                                    >
                                        {project.description
                                            ? project.description.length > 140
                                                ? `${project.description.slice(
                                                      0,
                                                      140
                                                  )}…`
                                                : project.description
                                            : "No description"}
                                    </p>

                                    {(project.start_date || project.due_date) && (
                                        <p className="projects-panel-card-dates">
                                            {project.start_date
                                                ? `Start: ${project.start_date}`
                                                : ""}
                                            {project.start_date &&
                                            project.due_date
                                                ? " · "
                                                : ""}
                                            {project.due_date
                                                ? `Due: ${project.due_date}`
                                                : ""}
                                        </p>
                                    )}

                                    {project.member_count !== undefined && (
                                        <p className="pp-member-count">
                                            {project.member_count}{" "}
                                            {project.member_count === 1
                                                ? "member"
                                                : "members"}
                                        </p>
                                    )}

                                    <div className="projects-panel-card-actions">
                                        <button
                                            type="button"
                                            className="dashboard-button dashboard-button--primary"
                                            onClick={() =>
                                                onSelectProject?.(project.id)
                                            }
                                        >
                                            Open tasks
                                        </button>

                                        {canEdit && (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--ghost"
                                                onClick={() =>
                                                    setEditProject(project)
                                                }
                                                data-cy={`edit-project-${project.id}`}
                                            >
                                                Edit
                                            </button>
                                        )}

                                        {canDelete && (
                                            <button
                                                type="button"
                                                className="dashboard-button dashboard-button--danger"
                                                onClick={() =>
                                                    setDeleteTarget(project)
                                                }
                                                data-cy={`delete-project-${project.id}`}
                                            >
                                                Delete
                                            </button>
                                        )}
                                    </div>
                                </article>
                            );
                        })}
                    </div>
                )}

                {/* Load more */}
                {hasMore && !loading && (
                    <div className="pp-load-more">
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--ghost"
                            onClick={handleLoadMore}
                            disabled={loadingMore}
                        >
                            {loadingMore
                                ? "Loading more"
                                : `Load more (${total - projects.length} remaining)`}
                        </button>
                    </div>
                )}
            </section>

            {/* ── Modals ───────────────────────────────────────────────────── */}

            <ProjectFormModal
                open={showCreate}
                project={null}
                onClose={() => setShowCreate(false)}
                onSaved={handleSaved}
            />

            <ProjectFormModal
                open={Boolean(editProject)}
                project={editProject}
                onClose={() => setEditProject(null)}
                onSaved={handleSaved}
            />


            {/* Delete confirmation */}
            {deleteTarget && (
                <div className="pm-overlay" role="dialog" aria-modal="true">
                    <div className="pm-dialog pm-dialog--confirm">
                        <div className="pm-header">
                            <h2 className="pm-title">Delete Project</h2>
                        </div>
                        <p className="pm-confirm-text">
                            Are you sure you want to permanently delete{" "}
                            <strong>{deleteTarget.name}</strong>? This will also
                            remove all associated tasks. This cannot be undone.
                        </p>
                        {deleteError && (
                            <div className="pm-error" role="alert">
                                {deleteError}
                            </div>
                        )}
                        <div className="pm-actions">
                            <button
                                type="button"
                                className="dashboard-button dashboard-button--ghost"
                                onClick={() => {
                                    setDeleteTarget(null);
                                    setDeleteError(null);
                                }}
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="dashboard-button dashboard-button--danger"
                                onClick={handleDeleteConfirm}
                                disabled={deleting}
                            >
                                {deleting ? "Deleting…" : "Delete project"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

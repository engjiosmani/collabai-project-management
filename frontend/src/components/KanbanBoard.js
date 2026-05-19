import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../api/api";
import TaskDescriptionMarkdown from "./TaskDescriptionMarkdown";
import "./KanbanBoard.css";

// ─── helpers ────────────────────────────────────────────────────────────────

function groupByStatus(tasks, statuses) {
    const map = {};
    statuses.forEach((s) => (map[s.id] = []));
    tasks.forEach((t) => {
        const sid = t.status ?? "unset";
        if (!map[sid]) map[sid] = [];
        map[sid].push(t);
    });
    return map;
}

function descriptionPreview(text, maxLen = 100) {
    if (!text) return "";
    const plain = text
        .replace(/^#+\s*/gm, "")
        .replace(/\*\*/g, "")
        .replace(/\r\n/g, "\n")
        .trim();
    const firstLine = plain.split("\n").find((line) => line.trim()) || plain;
    if (firstLine.length <= maxLen) return firstLine;
    return `${firstLine.slice(0, maxLen)}…`;
}

function statusName(statuses, statusId) {
    return statuses.find((s) => s.id === statusId)?.name || "—";
}

// ─── sub-components ─────────────────────────────────────────────────────────

function PriorityBadge({ name }) {
    if (!name) return null;
    const tone =
        name.toLowerCase().includes("high") || name.toLowerCase().includes("critical")
            ? "high"
            : name.toLowerCase().includes("low")
            ? "low"
            : "med";
    return <span className={`kb-badge kb-badge--${tone}`}>{name}</span>;
}

function TaskCard({ task, statuses, onStatusChange, onEdit, onView, projectName }) {
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const dragStartedRef = useRef(false);

    const handleStatusSelect = async (newStatusId) => {
        setSaving(true);
        setOpen(false);
        await onStatusChange(task.id, Number(newStatusId));
        setSaving(false);
    };

    const preview = descriptionPreview(task.description);

    const handleBodyClick = () => {
        if (dragStartedRef.current) {
            dragStartedRef.current = false;
            return;
        }
        onView(task);
    };

    return (
        <div
            className="kb-card"
            data-cy={`task-card-${task.id}`}
            draggable
            onDragStart={(e) => {
                dragStartedRef.current = true;
                e.dataTransfer.setData("taskId", String(task.id));
            }}
            onDragEnd={() => {
                window.setTimeout(() => {
                    dragStartedRef.current = false;
                }, 0);
            }}
        >
            <button
                type="button"
                className="kb-card-body"
                onClick={handleBodyClick}
                aria-label={`View details for ${task.title}`}
            >
                <p className="kb-card-title">{task.title}</p>
                {preview ? (
                    <p className="kb-card-desc">{preview}</p>
                ) : (
                    <p className="kb-card-desc kb-card-desc--muted">No description</p>
                )}
            </button>

            <div className="kb-card-meta">
                {projectName ? (
                    <span className="kb-card-project" title={projectName}>
                        {projectName}
                    </span>
                ) : null}
                <PriorityBadge name={task.priority_name} />
                {task.due_date && (
                    <span className="kb-card-due">📅 {task.due_date}</span>
                )}
                {task.assigned_to_email && (
                    <span className="kb-card-assignee" title={task.assigned_to_email}>
                        {task.assigned_to_email.split("@")[0]}
                    </span>
                )}
            </div>

            <div className="kb-card-actions">
                <div className="kb-status-picker">
                    <button
                        className="kb-btn kb-btn--sm"
                        onClick={() => setOpen((v) => !v)}
                        disabled={saving}
                        type="button"
                    >
                        {saving ? "Saving…" : "Move ▾"}
                    </button>

                    {open && (
                        <ul className="kb-dropdown" role="listbox">
                            {statuses.map((s) => (
                                <li
                                    key={s.id}
                                    role="option"
                                    aria-selected={task.status === s.id}
                                    className={`kb-dropdown-item${task.status === s.id ? " kb-dropdown-item--active" : ""}`}
                                    onClick={() => handleStatusSelect(s.id)}
                                >
                                    {s.name}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <button
                    className="kb-btn kb-btn--ghost kb-btn--sm"
                    onClick={() => onEdit(task)}
                    type="button"
                >
                    Edit
                </button>
            </div>
        </div>
    );
}

function TaskDetailModal({ task, statuses, onClose, onEdit }) {
    if (!task) return null;

    return (
        <div className="kb-modal-backdrop" onClick={onClose} data-cy="task-detail-backdrop">
            <div
                className="kb-modal kb-modal--detail"
                data-cy="task-detail-modal"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <div className="kb-modal-header">
                    <h3 id="task-detail-title">{task.title}</h3>
                    <button className="kb-modal-close" onClick={onClose} type="button" aria-label="Close">
                        ✕
                    </button>
                </div>

                <div className="kb-detail-meta">
                    <PriorityBadge name={task.priority_name} />
                    <span className="kb-detail-status">{statusName(statuses, task.status)}</span>
                    {task.due_date && <span className="kb-card-due">📅 {task.due_date}</span>}
                    {task.assigned_to_email && (
                        <span className="kb-card-assignee" title={task.assigned_to_email}>
                            {task.assigned_to_email.split("@")[0]}
                        </span>
                    )}
                </div>

                <div className="kb-detail-section">
                    <h4 className="kb-detail-label">Description</h4>
                    {task.description ? (
                        <div className="kb-detail-description">
                            <TaskDescriptionMarkdown text={task.description} />
                        </div>
                    ) : (
                        <p className="kb-detail-empty">No description for this task.</p>
                    )}
                </div>

                <div className="kb-modal-footer">
                    <button className="kb-btn kb-btn--ghost" onClick={onClose} type="button">
                        Close
                    </button>
                    <button
                        className="kb-btn kb-btn--primary"
                        onClick={() => onEdit(task)}
                        type="button"
                        data-cy="task-detail-edit"
                    >
                        Edit task
                    </button>
                </div>
            </div>
        </div>
    );
}

function Column({ status, tasks, statuses, onStatusChange, onEdit, onView, onDrop, projectNameById, showProject }) {
    const [over, setOver] = useState(false);

    return (
        <div
            className={`kb-column${over ? " kb-column--over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
                e.preventDefault();
                setOver(false);
                const taskId = Number(e.dataTransfer.getData("taskId"));
                if (taskId) onDrop(taskId, status.id);
            }}
        >
            <div className="kb-column-header">
                <span className="kb-column-title">{status.name}</span>
                <span className="kb-column-count">{tasks.length}</span>
            </div>

            <div className="kb-column-body">
                {tasks.map((t) => (
                    <TaskCard
                        key={t.id}
                        task={t}
                        statuses={statuses}
                        onStatusChange={onStatusChange}
                        onEdit={onEdit}
                        onView={onView}
                        projectName={showProject ? projectNameById.get(t.project) : null}
                    />
                ))}
                {tasks.length === 0 && (
                    <div className="kb-column-empty">Drop tasks here</div>
                )}
            </div>
        </div>
    );
}

function TaskModal({ task, statuses, onClose, onSaved, defaultProjectId }) {
    const isNew = !task;
    const [form, setForm] = useState({
        title: task?.title ?? "",
        description: task?.description ?? "",
        status: task?.status ?? (statuses[0]?.id ?? ""),
        due_date: task?.due_date ?? "",
        project: task?.project ?? defaultProjectId ?? "",
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [projects, setProjects] = useState([]);
    const [projectsLoading, setProjectsLoading] = useState(true);

    const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

    useEffect(() => {
        let cancelled = false;

        const loadProjects = async () => {
            setProjectsLoading(true);

            try {
                const res = await API.get("/projects/");
                const projectList = Array.isArray(res.data) ? res.data : res.data.results ?? [];

                if (cancelled) {
                    return;
                }

                setProjects(projectList);

                setForm((current) => {
                    if (current.project || task?.project) {
                        return current;
                    }

                    const fallback =
                        defaultProjectId ||
                        projectList[0]?.id ||
                        "";
                    return {
                        ...current,
                        project: fallback,
                    };
                });
            } catch (err) {
                if (!cancelled) {
                    setError(err.response?.data?.detail ?? "Failed to load projects.");
                }
            } finally {
                if (!cancelled) {
                    setProjectsLoading(false);
                }
            }
        };

        loadProjects();

        return () => {
            cancelled = true;
        };
    }, [task?.project, defaultProjectId]);

    const handleSubmit = async () => {
        if (!form.title.trim()) { setError("Title is required."); return; }
        if (!form.project) { setError("Project selection is required."); return; }
        setSaving(true);
        setError(null);
        try {
            const payload = {
                title: form.title.trim(),
                description: form.description,
                status: form.status || null,
                due_date: form.due_date || null,
                project: Number(form.project),
            };
            let saved;
            if (isNew) {
                const res = await API.post("/tasks/", payload);
                saved = res.data;
            } else {
                const res = await API.patch(`/tasks/${task.id}/`, payload);
                saved = res.data;
            }
            onSaved(saved, isNew);
        } catch (err) {
            const data = err.response?.data;
            setError(data ? JSON.stringify(data) : "Save failed.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="kb-modal-backdrop" onClick={onClose}>
            <div className="kb-modal" data-cy="task-modal" onClick={(e) => e.stopPropagation()}>
                <div className="kb-modal-header">
                    <h3>{isNew ? "New task" : "Edit task"}</h3>
                    <button className="kb-modal-close" data-cy="task-modal-close" onClick={onClose} type="button">✕</button>
                </div>

                {error && <p className="kb-modal-error">{error}</p>}

                <label className="kb-label">
                    Title *
                    <input className="kb-input" data-cy="task-title" value={form.title} onChange={set("title")} />
                </label>

                <label className="kb-label">
                    Description
                    <textarea className="kb-input kb-textarea" data-cy="task-description" value={form.description} onChange={set("description")} rows={3} />
                </label>

                <label className="kb-label">
                    Status
                    <select className="kb-input" data-cy="task-status" value={form.status} onChange={set("status")}>
                        {statuses.map((s) => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                    </select>
                </label>

                <label className="kb-label">
                    Due date
                    <input className="kb-input" data-cy="task-due-date" type="date" value={form.due_date} onChange={set("due_date")} />
                </label>

                <label className="kb-label">
                    Project *
                    <select className="kb-input" data-cy="task-project" value={form.project} onChange={set("project")} disabled={projectsLoading || projects.length === 0}>
                        <option value="">{projectsLoading ? "Loading projects..." : "Select a project"}</option>
                        {projects.map((project) => (
                            <option key={project.id} value={project.id}>
                                {project.name}
                            </option>
                        ))}
                    </select>
                    {!projectsLoading && projects.length === 0 ? (
                        <p className="kb-modal-error">No accessible projects found. Create or join a project first.</p>
                    ) : null}
                </label>

                <div className="kb-modal-footer">
                    <button className="kb-btn kb-btn--ghost" data-cy="task-cancel" onClick={onClose} type="button">Cancel</button>
                    <button className="kb-btn kb-btn--primary" data-cy="task-save" onClick={handleSubmit} disabled={saving} type="button">
                        {saving ? "Saving…" : isNew ? "Create" : "Save"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function KanbanBoard({
    onTasksChanged,
    projectFilter: projectFilterProp,
    onProjectFilterChange,
}) {
    const [tasks, setTasks] = useState([]);
    const [statuses, setStatuses] = useState([]);
    const [projects, setProjects] = useState([]);
    const [internalProjectFilter, setInternalProjectFilter] = useState("");
    const projectFilter =
        onProjectFilterChange !== undefined ? (projectFilterProp ?? "") : internalProjectFilter;
    const setProjectFilter = onProjectFilterChange ?? setInternalProjectFilter;
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editingTask, setEditingTask] = useState(undefined); // undefined = closed, null = new
    const [viewingTask, setViewingTask] = useState(null);
    const abortRef = useRef(null);

    const projectNameById = useMemo(() => {
        const map = new Map();
        projects.forEach((p) => map.set(p.id, p.name));
        return map;
    }, [projects]);

    const showProjectOnCards = !projectFilter;

    // ── fetch ──────────────────────────────────────────────────────────────

    const fetchAll = useCallback(async () => {
        if (abortRef.current) abortRef.current.abort();
        abortRef.current = new AbortController();
        setLoading(true);
        setError(null);
        try {
            const taskParams = projectFilter ? { project: projectFilter } : {};
            const [taskRes, statusRes, projectRes] = await Promise.all([
                API.get("/tasks/", {
                    params: taskParams,
                    signal: abortRef.current.signal,
                }),
                API.get("/task-statuses/", { signal: abortRef.current.signal }),
                API.get("/projects/", { signal: abortRef.current.signal }),
            ]);

            const taskList = Array.isArray(taskRes.data)
                ? taskRes.data
                : taskRes.data.results ?? [];
            const statusList = Array.isArray(statusRes.data)
                ? statusRes.data
                : statusRes.data.results ?? [];
            const projectList = Array.isArray(projectRes.data)
                ? projectRes.data
                : projectRes.data.results ?? [];

            setTasks(taskList);
            setStatuses(statusList);
            setProjects(projectList);
        } catch (err) {
            if (err.name === "CanceledError" || err.name === "AbortError") return;
            setError(err.response?.data?.detail ?? "Failed to load board.");
        } finally {
            setLoading(false);
        }
    }, [projectFilter]);

    useEffect(() => {
        fetchAll();
        return () => abortRef.current?.abort();
    }, [fetchAll]);

    // ── status change (drag-and-drop or dropdown) ──────────────────────────

    const handleStatusChange = useCallback(async (taskId, newStatusId) => {
        const previous = tasks.find((t) => t.id === taskId);
        setTasks((prev) =>
            prev.map((t) => (t.id === taskId ? { ...t, status: newStatusId } : t))
        );
        try {
            const res = await API.patch(`/tasks/${taskId}/`, { status: newStatusId });
            setTasks((prev) =>
                prev.map((t) => (t.id === taskId ? { ...t, ...res.data } : t))
            );
            onTasksChanged?.();
        } catch {
            if (previous) {
                setTasks((prev) =>
                    prev.map((t) => (t.id === taskId ? { ...t, status: previous.status } : t))
                );
            } else {
                fetchAll();
            }
        }
    }, [fetchAll, onTasksChanged, tasks]);

    // ── modal callbacks ────────────────────────────────────────────────────

    const handleSaved = (saved, isNew) => {
        const matchesFilter =
            !projectFilter || String(saved.project) === String(projectFilter);

        if (isNew) {
            if (matchesFilter) {
                setTasks((prev) => [saved, ...prev]);
            }
        } else if (matchesFilter) {
            setTasks((prev) => prev.map((t) => (t.id === saved.id ? saved : t)));
        } else {
            setTasks((prev) => prev.filter((t) => t.id !== saved.id));
        }
        setEditingTask(undefined);
        onTasksChanged?.();
    };

    const visibleTasks = useMemo(() => {
        if (!projectFilter) return tasks;
        return tasks.filter((t) => String(t.project) === String(projectFilter));
    }, [tasks, projectFilter]);

    const grouped = groupByStatus(visibleTasks, statuses);

    // ── render ─────────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="kb-state kb-state--loading" data-cy="kanban-loading">
                <div className="kb-spinner" />
                <span>Loading board…</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="kb-state kb-state--error" data-cy="kanban-error">
                <p>{error}</p>
                <button className="kb-btn kb-btn--primary" onClick={fetchAll} type="button">Retry</button>
            </div>
        );
    }

    return (
        <div className="kb-root">
            <header className="kb-header">
                <h2 className="kb-header__title" data-cy="kanban-title">
                    Kanban task board
                </h2>
                <div className="kb-header__controls">
                    <label className="kb-filter">
                        <span className="kb-filter-label">Project</span>
                        <select
                            className="kb-filter-select"
                            data-cy="kanban-project-filter"
                            value={projectFilter}
                            onChange={(e) => setProjectFilter(e.target.value)}
                            aria-label="Filter tasks by project"
                        >
                            <option value="">All projects</option>
                            {projects.map((p) => (
                                <option key={p.id} value={String(p.id)}>
                                    {p.name}
                                </option>
                            ))}
                        </select>
                    </label>
                    <button
                        className="kb-btn kb-btn--primary"
                        data-cy="new-task-button"
                        onClick={() => setEditingTask(null)}
                        type="button"
                        disabled={projects.length === 0}
                    >
                        + New task
                    </button>
                </div>
                <p className="kb-header__desc">
                    Create tasks, move them between columns, and filter by project.
                </p>
            </header>

            {statuses.length === 0 ? (
                <div className="kb-state kb-state--empty">
                    No task statuses found. Make sure the backend has TaskStatus records.
                </div>
            ) : (
                <div className="kb-board">
                    {statuses.map((s) => (
                        <Column
                            key={s.id}
                            status={s}
                            tasks={grouped[s.id] ?? []}
                            statuses={statuses}
                            onStatusChange={handleStatusChange}
                            onEdit={(t) => setEditingTask(t)}
                            onView={(t) => setViewingTask(t)}
                            onDrop={handleStatusChange}
                            projectNameById={projectNameById}
                            showProject={showProjectOnCards}
                        />
                    ))}
                </div>
            )}

            {viewingTask && (
                <TaskDetailModal
                    task={viewingTask}
                    statuses={statuses}
                    onClose={() => setViewingTask(null)}
                    onEdit={(t) => {
                        setViewingTask(null);
                        setEditingTask(t);
                    }}
                />
            )}

            {editingTask !== undefined && (
                <TaskModal
                    task={editingTask}
                    statuses={statuses}
                    onClose={() => setEditingTask(undefined)}
                    onSaved={handleSaved}
                    defaultProjectId={projectFilter ? Number(projectFilter) : undefined}
                />
            )}
        </div>
    );
}

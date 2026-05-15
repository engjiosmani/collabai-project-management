import { useCallback, useEffect, useRef, useState } from "react";
import API from "../api/api";
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

function TaskCard({ task, statuses, onStatusChange, onEdit }) {
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    const handleStatusSelect = async (newStatusId) => {
        setSaving(true);
        setOpen(false);
        await onStatusChange(task.id, Number(newStatusId));
        setSaving(false);
    };

    return (
        <div
            className="kb-card"
            data-cy={`task-card-${task.id}`}
            draggable
            onDragStart={(e) => {
                e.dataTransfer.setData("taskId", String(task.id));
            }}
        >
            <p className="kb-card-title">{task.title}</p>

            {task.description ? (
                <p className="kb-card-desc">{task.description.slice(0, 80)}{task.description.length > 80 ? "…" : ""}</p>
            ) : null}

            <div className="kb-card-meta">
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

function Column({ status, tasks, statuses, onStatusChange, onEdit, onDrop }) {
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
                    />
                ))}
                {tasks.length === 0 && (
                    <div className="kb-column-empty">Drop tasks here</div>
                )}
            </div>
        </div>
    );
}

function TaskModal({ task, statuses, onClose, onSaved }) {
    const isNew = !task;
    const [form, setForm] = useState({
        title: task?.title ?? "",
        description: task?.description ?? "",
        status: task?.status ?? (statuses[0]?.id ?? ""),
        due_date: task?.due_date ?? "",
        project: task?.project ?? "",
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

                    return {
                        ...current,
                        project: projectList[0]?.id ?? "",
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
    }, [task?.project]);

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

export default function KanbanBoard() {
    const [tasks, setTasks] = useState([]);
    const [statuses, setStatuses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editingTask, setEditingTask] = useState(undefined); // undefined = closed, null = new
    const abortRef = useRef(null);

    // ── fetch ──────────────────────────────────────────────────────────────

    const fetchAll = useCallback(async () => {
        if (abortRef.current) abortRef.current.abort();
        abortRef.current = new AbortController();
        setLoading(true);
        setError(null);
        try {
            const [taskRes, statusRes] = await Promise.all([
                API.get("/tasks/", { signal: abortRef.current.signal }),
                API.get("/task-statuses/", { signal: abortRef.current.signal }),
            ]);

            // handle paginated or plain list
            const taskList = Array.isArray(taskRes.data)
                ? taskRes.data
                : taskRes.data.results ?? [];
            const statusList = Array.isArray(statusRes.data)
                ? statusRes.data
                : statusRes.data.results ?? [];

            setTasks(taskList);
            setStatuses(statusList);
        } catch (err) {
            if (err.name === "CanceledError" || err.name === "AbortError") return;
            setError(err.response?.data?.detail ?? "Failed to load board.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();
        return () => abortRef.current?.abort();
    }, [fetchAll]);

    // ── status change (drag-and-drop or dropdown) ──────────────────────────

    const handleStatusChange = useCallback(async (taskId, newStatusId) => {
        // optimistic update
        setTasks((prev) =>
            prev.map((t) => (t.id === taskId ? { ...t, status: newStatusId } : t))
        );
        try {
            const res = await API.patch(`/tasks/${taskId}/`, { status: newStatusId });
            setTasks((prev) =>
                prev.map((t) => (t.id === taskId ? { ...t, ...res.data } : t))
            );
        } catch {
            // revert
            fetchAll();
        }
    }, [fetchAll]);

    // ── modal callbacks ────────────────────────────────────────────────────

    const handleSaved = (saved, isNew) => {
        if (isNew) {
            setTasks((prev) => [saved, ...prev]);
        } else {
            setTasks((prev) => prev.map((t) => (t.id === saved.id ? saved : t)));
        }
        setEditingTask(undefined);
    };

    const grouped = groupByStatus(tasks, statuses);

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
            <div className="kb-toolbar">
                <h2 className="kb-toolbar-title" data-cy="kanban-title">Kanban Board</h2>
                <button
                    className="kb-btn kb-btn--primary"
                    data-cy="new-task-button"
                    onClick={() => setEditingTask(null)}
                    type="button"
                >
                    + New task
                </button>
            </div>

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
                            onDrop={handleStatusChange}
                        />
                    ))}
                </div>
            )}

            {editingTask !== undefined && (
                <TaskModal
                    task={editingTask}
                    statuses={statuses}
                    onClose={() => setEditingTask(undefined)}
                    onSaved={handleSaved}
                />
            )}
        </div>
    );
}

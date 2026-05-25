import axios from "axios";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API, { getApiErrorMessage } from "../api/api";
import { getOrganizationMembers } from "../api/organizations";
import {
    createTask,
    createTaskComment,
    downloadTaskAttachment,
    deleteTask,
    deleteTaskAttachment,
    getTaskActivityLogs,
    getTaskAttachments,
    getTaskComments,
    getTaskPriorities,
    getTaskStatuses,
    getTasks,
    updateTask,
    uploadTaskAttachment,
} from "../api/tasks";
import { fetchProjectMembers } from "../api/projects";
import { getWorkspaceMembers } from "../api/workspaces";
import TaskDescriptionMarkdown from "./TaskDescriptionMarkdown";
import EmptyState from "./ui/EmptyState";
import LoadingSkeleton from "./ui/LoadingSkeleton";
import LoadingSpinner from "./ui/LoadingSpinner";
import { useOrganization } from "../context/OrganizationContext";
import { useRole } from "../hooks/useRole";
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

function getMemberUserId(member) {
    if (!member) return "";
    if (member.user_id !== undefined && member.user_id !== null) return member.user_id;
    if (member.user?.id !== undefined && member.user?.id !== null) return member.user.id;
    if (typeof member.user === "number" || typeof member.user === "string") return member.user;
    if (member.id !== undefined && member.email && !member.organization && !member.workspace && !member.project) return member.id;
    return "";
}

function toAssigneeOption(member) {
    const userId = getMemberUserId(member);
    return {
        ...member,
        user_id: userId,
        email: member.email ?? member.user_email ?? member.user?.email ?? "",
        username: member.username ?? member.user?.username ?? "",
    };
}

function toProjectMemberAssignee(member) {
    const userId = getMemberUserId(member);
    return {
        ...member,
        user_id: userId,
        email: member.email ?? member.user_email ?? member.user?.email ?? "",
        username: member.username ?? member.user_username ?? member.user?.username ?? "",
    };
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

function DeleteTaskDialog({ open, taskTitle, saving, onConfirm, onCancel }) {
    if (!open) return null;

    return (
        <div className="kb-modal-backdrop" onClick={onCancel} data-cy="delete-task-backdrop">
            <div className="kb-modal kb-modal--confirm" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="kb-modal-header">
                    <h3>Delete task</h3>
                    <button className="kb-modal-close" type="button" onClick={onCancel} aria-label="Close delete dialog">
                        ✕
                    </button>
                </div>
                <p className="kb-detail-empty">
                    Delete <strong>{taskTitle}</strong>? This cannot be undone.
                </p>
                <div className="kb-modal-footer">
                    <button className="kb-btn kb-btn--ghost" type="button" onClick={onCancel} disabled={saving}>
                        Cancel
                    </button>
                    <button className="kb-btn kb-btn--danger" type="button" onClick={onConfirm} disabled={saving}>
                        {saving ? "Deleting…" : "Delete task"}
                    </button>
                </div>
            </div>
        </div>
    );
}

function TaskCard({ task, statuses, onStatusChange, onEdit, onView, projectName, canMoveTask, canEditTask }) {
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const dragStartedRef = useRef(false);

    const handleStatusSelect = async (newStatusId) => {
        if (!canMoveTask) return;
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
            draggable={canMoveTask}
            onDragStart={(e) => {
                if (!canMoveTask) {
                    e.preventDefault();
                    return;
                }
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
                {canMoveTask && (
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
                )}

                {canEditTask ? (
                    <button
                        className="kb-btn kb-btn--ghost kb-btn--sm"
                        onClick={() => onEdit(task)}
                        type="button"
                    >
                        Edit
                    </button>
                ) : null}
            </div>
        </div>
    );
}

function TaskDetailModal({ task, statuses, onClose, onEdit, onDeleted, canDeleteTask, canEditTask, canManageAttachments, canUploadAttachments, currentUserId }) {
    const [attachments, setAttachments] = useState([]);
    const [comments, setComments] = useState([]);
    const [activity, setActivity] = useState([]);
    const [attachmentsLoading, setAttachmentsLoading] = useState(true);
    const [commentsLoading, setCommentsLoading] = useState(true);
    const [activityLoading, setActivityLoading] = useState(true);
    const [attachmentsError, setAttachmentsError] = useState("");
    const [commentsError, setCommentsError] = useState("");
    const [activityError, setActivityError] = useState("");
    const [commentContent, setCommentContent] = useState("");
    const [savingComment, setSavingComment] = useState(false);
    const [attachmentPickerOpen, setAttachmentPickerOpen] = useState(false);
    const [attachmentFile, setAttachmentFile] = useState(null);
    const [savingAttachment, setSavingAttachment] = useState(false);
    const [deletingAttachmentId, setDeletingAttachmentId] = useState(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (!task?.id) return;

        let cancelled = false;
        const controller = new AbortController();

        const loadData = async () => {
            setAttachmentsLoading(true);
            setCommentsLoading(true);
            setActivityLoading(true);
            setAttachmentsError("");
            setCommentsError("");
            setActivityError("");

            try {
                const [attachmentData, commentData, activityData] = await Promise.all([
                    getTaskAttachments(task.id, controller.signal),
                    getTaskComments(task.id, controller.signal),
                    getTaskActivityLogs(task.id, controller.signal),
                ]);

                if (cancelled) return;

                setAttachments(attachmentData);
                setComments(commentData);
                setActivity(activityData);
            } catch (requestError) {
                if (cancelled || requestError?.code === "ERR_CANCELED") return;
                const message = getApiErrorMessage(requestError, "Failed to load task details.");
                setAttachmentsError(message);
                setCommentsError(message);
                setActivityError(message);
            } finally {
                if (!cancelled) {
                    setAttachmentsLoading(false);
                    setCommentsLoading(false);
                    setActivityLoading(false);
                }
            }
        };

        loadData();

        return () => {
            cancelled = true;
            controller.abort();
        };
    }, [task?.id]);

    const handleDownloadAttachment = async (attachment) => {
        try {
            const blob = await downloadTaskAttachment(task.id, attachment.id);
            const objectUrl = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = attachment.file_name || "attachment";
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(objectUrl);
        } catch (requestError) {
            setAttachmentsError(getApiErrorMessage(requestError, "Failed to download attachment."));
        }
    };

    const handleSelectAttachment = (event) => {
        setAttachmentFile(event.target.files?.[0] || null);
    };

    const handleUploadAttachment = async () => {
        if (!attachmentFile) return;

        setSavingAttachment(true);
        setAttachmentsError("");
        try {
            const saved = await uploadTaskAttachment(task.id, attachmentFile);
            setAttachments((current) => [saved, ...current]);
            setAttachmentFile(null);
            setAttachmentPickerOpen(false);
        } catch (requestError) {
            setAttachmentsError(getApiErrorMessage(requestError, "Failed to upload attachment."));
        } finally {
            setSavingAttachment(false);
        }
    };

    const handleDeleteAttachment = async (attachment) => {
        setDeletingAttachmentId(attachment.id);
        setAttachmentsError("");
        try {
            await deleteTaskAttachment(task.id, attachment.id);
            setAttachments((current) => current.filter((item) => item.id !== attachment.id));
        } catch (requestError) {
            setAttachmentsError(getApiErrorMessage(requestError, "Failed to delete attachment."));
        } finally {
            setDeletingAttachmentId(null);
        }
    };

    const handleSubmitComment = async (event) => {
        event.preventDefault();
        const text = commentContent.trim();
        if (!text) return;

        setSavingComment(true);
        setCommentsError("");
        try {
            const saved = await createTaskComment({ task: task.id, content: text });
            setComments((current) => [...current, saved]);
            setCommentContent("");
        } catch (requestError) {
            setCommentsError(getApiErrorMessage(requestError, "Failed to add comment."));
        } finally {
            setSavingComment(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await onDeleted(task);
            setDeleteOpen(false);
        } finally {
            setDeleting(false);
        }
    };

    if (!task) return null;

    const labelItems = Array.isArray(task.labels) ? task.labels : [];

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

                <div className="kb-modal-body kb-modal-body--detail">
                    <div className="kb-detail-meta">
                        <PriorityBadge name={task.priority_name} />
                        <span className="kb-detail-status">{statusName(statuses, task.status)}</span>
                        {task.due_date ? <span className="kb-card-due">📅 {task.due_date}</span> : null}
                        {task.assigned_to_email ? (
                            <span className="kb-card-assignee" title={task.assigned_to_email}>
                                {task.assigned_to_email.split("@")[0]}
                            </span>
                        ) : null}
                    </div>

                    {labelItems.length ? (
                        <div className="kb-detail-tags">
                            {labelItems.map((label) => (
                                <span key={label.id || label.name} className="kb-detail-tag">
                                    {label.name}
                                </span>
                            ))}
                        </div>
                    ) : null}

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

                    <div className="kb-detail-section">
                        <h4 className="kb-detail-label">Attachments</h4>
                        {attachmentsLoading ? (
                            <LoadingSkeleton
                                variant="list"
                                count={2}
                                lines={1}
                                label="Loading attachments"
                            />
                        ) : null}
                        {attachmentsError ? <p className="kb-modal-error">{attachmentsError}</p> : null}
                        {!attachmentsLoading && attachments.length === 0 ? (
                            <EmptyState
                                compact
                                icon="A"
                                title="No attachments"
                                description="Files added to this task will appear here."
                            />
                        ) : null}
                        <div className="kb-detail-list">
                            {attachments.map((attachment) => {
                                const canDeleteAttachment =
                                    canManageAttachments ||
                                    String(attachment.uploaded_by || "") === String(currentUserId || "");
                                return (
                                <article key={attachment.id} className="kb-detail-item">
                                    <div className="kb-detail-item__topline">
                                        <div className="kb-detail-item__meta">
                                            <strong>{attachment.file_name}</strong>
                                            <span>{attachment.uploaded_by_email || "Uploaded"}</span>
                                        </div>
                                        {canDeleteAttachment && (
                                            <button
                                                className="kb-detail-item__remove"
                                                type="button"
                                                onClick={() => handleDeleteAttachment(attachment)}
                                                disabled={deletingAttachmentId === attachment.id}
                                                aria-label={`Remove ${attachment.file_name}`}
                                                title="Remove attachment"
                                            >
                                                ×
                                            </button>
                                        )}
                                    </div>
                                    <button className="kb-btn kb-btn--ghost kb-btn--sm" type="button" onClick={() => handleDownloadAttachment(attachment)}>
                                        Download
                                    </button>
                                </article>
                            );
                            })}
                        </div>
                        {canUploadAttachments && !attachmentPickerOpen ? (
                            <button
                                className="kb-btn kb-btn--primary kb-btn--sm"
                                type="button"
                                onClick={() => setAttachmentPickerOpen(true)}
                            >
                                Add attachment
                            </button>
                        ) : canUploadAttachments ? (
                            <div className="kb-attachment-picker">
                                <label className="kb-label">
                                    Choose file
                                    <input
                                        className="kb-input kb-file-input"
                                        type="file"
                                        onChange={handleSelectAttachment}
                                        disabled={savingAttachment}
                                    />
                                </label>
                                <div className="kb-attachment-picker__actions">
                                    <button
                                        className="kb-btn kb-btn--ghost"
                                        type="button"
                                        onClick={() => {
                                            setAttachmentPickerOpen(false);
                                            setAttachmentFile(null);
                                        }}
                                        disabled={savingAttachment}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        className="kb-btn kb-btn--primary"
                                        type="button"
                                        onClick={handleUploadAttachment}
                                        disabled={savingAttachment || !attachmentFile}
                                    >
                                        {savingAttachment ? "Uploading…" : "Upload attachment"}
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>

                    <div className="kb-detail-section">
                        <h4 className="kb-detail-label">Comments</h4>
                        {commentsLoading ? (
                            <LoadingSkeleton
                                variant="list"
                                count={2}
                                lines={2}
                                label="Loading comments"
                            />
                        ) : null}
                        {commentsError ? <p className="kb-modal-error">{commentsError}</p> : null}
                        {!commentsLoading && comments.length === 0 ? (
                            <EmptyState
                                compact
                                icon="C"
                                title="No comments"
                                description="Discussion about this task will appear here."
                            />
                        ) : null}
                        <div className="kb-detail-list">
                            {comments.map((comment) => (
                                <article key={comment.id} className="kb-detail-item">
                                    <div className="kb-detail-item__meta">
                                        <strong>{comment.author_email || "Unknown author"}</strong>
                                        <span>{comment.created_at ? new Date(comment.created_at).toLocaleString() : ""}</span>
                                    </div>
                                    <p>{comment.content}</p>
                                </article>
                            ))}
                        </div>
                        <form className="kb-detail-form" onSubmit={handleSubmitComment}>
                            <div className="kb-detail-form__field">
                                <textarea
                                    className="kb-input kb-textarea"
                                    rows={3}
                                    value={commentContent}
                                    onChange={(e) => setCommentContent(e.target.value)}
                                    placeholder="Add a comment"
                                />
                            </div>
                            <div className="kb-detail-form__actions">
                                <button className="kb-btn kb-btn--primary" type="submit" disabled={savingComment}>
                                    {savingComment ? "Posting…" : "Post comment"}
                                </button>
                            </div>
                        </form>
                    </div>

                    <div className="kb-detail-section">
                        <h4 className="kb-detail-label">Activity log</h4>
                        {activityLoading ? (
                            <LoadingSkeleton
                                variant="list"
                                count={2}
                                lines={2}
                                label="Loading activity"
                            />
                        ) : null}
                        {activityError ? <p className="kb-modal-error">{activityError}</p> : null}
                        {!activityLoading && activity.length === 0 ? (
                            <EmptyState
                                compact
                                icon="L"
                                title="No activity found"
                                description="Task updates, comments, and status changes will be listed here."
                            />
                        ) : null}
                        <div className="kb-detail-list">
                            {activity.map((item) => (
                                <article key={item.id} className="kb-detail-item">
                                    <div className="kb-detail-item__meta">
                                        <strong>{item.user_email || "Unknown user"}</strong>
                                        <span>{item.created_at ? new Date(item.created_at).toLocaleString() : ""}</span>
                                    </div>
                                    <p>
                                        <strong>{item.action}</strong>
                                        {item.description ? ` — ${item.description}` : ""}
                                    </p>
                                </article>
                            ))}
                        </div>
                    </div>

                </div>

                <div className="kb-modal-footer kb-modal-footer--sticky">
                    <button className="kb-btn kb-btn--ghost" onClick={onClose} type="button" data-cy="task-detail-close">
                        Close
                    </button>
                    {canEditTask ? (
                        <button
                            className="kb-btn kb-btn--primary"
                            onClick={() => onEdit(task)}
                            type="button"
                            data-cy="task-detail-edit"
                        >
                            Edit task
                        </button>
                    ) : null}
                    {canDeleteTask ? (
                        <button className="kb-btn kb-btn--danger" onClick={() => setDeleteOpen(true)} type="button" data-cy="task-detail-delete">
                            Delete
                        </button>
                    ) : null}
                </div>
            </div>

            <DeleteTaskDialog
                open={deleteOpen}
                taskTitle={task.title}
                saving={deleting}
                onCancel={() => setDeleteOpen(false)}
                onConfirm={handleDelete}
            />
        </div>
    );
}

function Column({ status, tasks, statuses, onStatusChange, onEdit, onView, onDrop, projectNameById, showProject, canMoveTask, canDropTasks, canEditTask }) {
    const [over, setOver] = useState(false);

    return (
        <div
            className={`kb-column${over ? " kb-column--over" : ""}`}
            onDragOver={(e) => {
                if (!canDropTasks) return;
                e.preventDefault();
                setOver(true);
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
                e.preventDefault();
                setOver(false);
                if (!canDropTasks) return;
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
                        canMoveTask={canMoveTask(t)}
                        canEditTask={canEditTask(t)}
                    />
                ))}
                {tasks.length === 0 && (
                    <EmptyState
                        compact
                        icon="T"
                        title="No tasks"
                        description="Tasks in this status will appear here."
                        className="kb-column-empty-state"
                    />
                )}
            </div>
        </div>
    );
}

function TaskModal({ task, statuses, priorities, projects, workspaceId, organizationId, canEditAllFields, onClose, onSaved, defaultProjectId }) {
    const isNew = !task;
    const todayDate = new Date().toISOString().slice(0, 10);
    const [form, setForm] = useState({
        title: task?.title ?? "",
        description: task?.description ?? "",
        status: String(task?.status ?? statuses[0]?.id ?? ""),
        priority: String(task?.priority ?? ""),
        due_date: task?.due_date ?? "",
        project: String(task?.project ?? defaultProjectId ?? ""),
        assigned_to: String(task?.assigned_to ?? ""),
        labels: Array.isArray(task?.labels) ? task.labels.map((label) => label.name) : [],
    });
    const [labelDraft, setLabelDraft] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [members, setMembers] = useState([]);
    const [membersLoading, setMembersLoading] = useState(false);
    const [membersError, setMembersError] = useState("");
    const selectedProject = useMemo(
        () => projects.find((project) => String(project.id) === String(form.project)),
        [form.project, projects]
    );
    const selectedProjectOrganizationId =
        selectedProject?.organization?.id ?? selectedProject?.organization ?? "";
    const assigneeOrganizationId = organizationId || selectedProjectOrganizationId;
    const assigneeWorkspaceId = selectedProject?.workspace || workspaceId;

    useEffect(() => {
        if (!task) {
            setForm((current) => ({
                ...current,
                status: current.status || String(statuses[0]?.id ?? ""),
                project: current.project || String(defaultProjectId ?? ""),
            }));
        }
    }, [defaultProjectId, statuses, task]);

    useEffect(() => {
        if (!task || form.priority) {
            return;
        }

        const matchedPriority =
            priorities.find((priority) => String(priority.id) === String(task.priority)) ||
            priorities.find((priority) => priority.name === task.priority_name);

        if (matchedPriority) {
            setForm((current) => ({
                ...current,
                priority: String(matchedPriority.id),
            }));
        }
    }, [form.priority, priorities, task]);

    useEffect(() => {
        let cancelled = false;

        const loadMembers = async () => {
            if (!assigneeWorkspaceId && !assigneeOrganizationId && !form.project) {
                setMembers([]);
                setMembersError("");
                return;
            }

            setMembersLoading(true);
            setMembersError("");
            try {
                let data = [];
                try {
                    data = assigneeWorkspaceId
                        ? await getWorkspaceMembers(assigneeWorkspaceId)
                        : await getOrganizationMembers(assigneeOrganizationId);
                } catch (sourceError) {
                    if (!form.project) {
                        throw sourceError;
                    }
                    const projectMembers = await fetchProjectMembers(form.project);
                    data = projectMembers.map(toProjectMemberAssignee);
                }
                if (!cancelled) {
                    setMembers(Array.isArray(data) ? data : []);
                }
            } catch {
                if (!cancelled) {
                    setMembers([]);
                    setMembersError("Could not load assignees. Try selecting a project with members.");
                }
            } finally {
                if (!cancelled) setMembersLoading(false);
            }
        };

        loadMembers();
        return () => {
            cancelled = true;
        };
    }, [assigneeOrganizationId, assigneeWorkspaceId, form.project]);

    const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

    const addLabel = (value) => {
        const text = (value || "").trim();
        if (!text) return;
        setForm((current) => {
            const exists = current.labels.some((label) => label.toLowerCase() === text.toLowerCase());
            if (exists) return current;
            return { ...current, labels: [...current.labels, text] };
        });
        setLabelDraft("");
    };

    const removeLabel = (value) => {
        setForm((current) => ({
            ...current,
            labels: current.labels.filter((label) => label !== value),
        }));
    };

    const handleLabelKeyDown = (event) => {
        if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            addLabel(labelDraft);
        }
        if (event.key === "Backspace" && !labelDraft && form.labels.length) {
            removeLabel(form.labels[form.labels.length - 1]);
        }
    };

    const handleSubmit = async () => {
        if (!form.title.trim()) {
            setError("Title is required.");
            return;
        }
        if (!form.project) {
            setError("Project selection is required.");
            return;
        }
        if (form.due_date && form.due_date < todayDate) {
            setError("Due date cannot be earlier than today.");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            const payload = canEditAllFields
                ? {
                    title: form.title.trim(),
                    description: form.description,
                    status: form.status || null,
                    priority: form.priority ? Number(form.priority) : null,
                    due_date: form.due_date || null,
                    project: Number(form.project),
                    assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
                    labels: form.labels,
                }
                : {
                    description: form.description,
                    status: form.status || null,
                };

            const saved = isNew ? await createTask(payload) : await updateTask(task.id, payload);
            onSaved(saved, isNew);
        } catch (err) {
            setError(getApiErrorMessage(err, "Save failed."));
        } finally {
            setSaving(false);
        }
    };

    const assigneeOptions = members
        .map(toAssigneeOption)
        .filter((member, index, list) =>
            member.user_id &&
            list.findIndex((candidate) => String(candidate.user_id) === String(member.user_id)) === index
        );

    const hasAssigneeSource = Boolean(assigneeWorkspaceId || assigneeOrganizationId || form.project);
    const memberEditOnly = !canEditAllFields;

    return (
        <div className="kb-modal-backdrop" onClick={onClose}>
            <div className="kb-modal kb-modal--detail" data-cy="task-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="kb-modal-header">
                    <h3>{isNew ? "New task" : "Edit task"}</h3>
                    <button className="kb-modal-close" data-cy="task-modal-close" onClick={onClose} type="button">✕</button>
                </div>

                {error && <p className="kb-modal-error">{error}</p>}
                {memberEditOnly ? <p className="kb-detail-empty">Members can update description and status only on assigned tasks.</p> : null}

                <div className="kb-modal-body kb-modal-body--detail">
                    <label className="kb-label">
                        Title *
                        <input className="kb-input" data-cy="task-title" value={form.title} onChange={set("title")} disabled={!canEditAllFields} />
                    </label>

                    <label className="kb-label">
                        Description
                        <textarea className="kb-input kb-textarea" data-cy="task-description" value={form.description} onChange={set("description")} rows={4} />
                    </label>

                    <div className="kb-edit-grid">
                        <label className="kb-label">
                            Status
                            <select className="kb-input" data-cy="task-status" value={form.status} onChange={set("status")}>
                                {statuses.map((s) => (
                                    <option key={s.id} value={s.id}>{s.name}</option>
                                ))}
                            </select>
                        </label>

                        <label className="kb-label">
                            Priority
                            <select className="kb-input" data-cy="task-priority" value={form.priority} onChange={set("priority")} disabled={!canEditAllFields}>
                                <option value="">No priority</option>
                                {priorities.map((priority) => (
                                    <option key={priority.id} value={priority.id}>{priority.name}</option>
                                ))}
                            </select>
                        </label>

                        <label className="kb-label">
                            Due date
                            <input className="kb-input" data-cy="task-due-date" type="date" min={todayDate} value={form.due_date} onChange={set("due_date")} disabled={!canEditAllFields} />
                        </label>

                        <label className="kb-label">
                            Project *
                            <select className="kb-input" data-cy="task-project" value={form.project} onChange={set("project")} disabled={projects.length === 0 || !canEditAllFields}>
                                <option value="">Select a project</option>
                                {projects.map((project) => (
                                    <option key={project.id} value={project.id}>
                                        {project.name}
                                    </option>
                                ))}
                            </select>
                            {!projects.length ? <p className="kb-modal-error">No accessible projects found. Create or join a project first.</p> : null}
                        </label>

                        <label className="kb-label">
                            Assignee
                            <select
                                className="kb-input"
                                data-cy="task-assignee"
                                value={form.assigned_to}
                                onChange={set("assigned_to")}
                                disabled={!hasAssigneeSource || membersLoading || !canEditAllFields}
                            >
                                <option value="">
                                    {membersLoading
                                        ? "Loading assignees"
                                        : hasAssigneeSource
                                        ? "Unassigned"
                                        : "Select a project first"}
                                </option>
                                {assigneeOptions.map((member) => (
                                    <option key={member.user_id} value={String(member.user_id)}>
                                        {member.email || member.username || `User ${member.user_id}`}
                                    </option>
                                ))}
                            </select>
                            {!membersError && canEditAllFields ? (
                                <p className="kb-detail-empty">
                                    {form.project
                                        ? "Only members of the selected project's workspace can be assigned."
                                        : "Select a project before choosing an assignee."}
                                </p>
                            ) : null}
                            {membersError ? <p className="kb-modal-error">{membersError}</p> : null}
                        </label>

                        <label className="kb-label" style={{ gridColumn: "1 / -1" }}>
                            Labels
                            <div className="kb-tag-input">
                                <div className="kb-tag-input__chips">
                                    {form.labels.map((label) => (
                                        <button
                                            key={label}
                                            type="button"
                                            className="kb-detail-tag kb-detail-tag--removable"
                                            onClick={() => removeLabel(label)}
                                            disabled={!canEditAllFields}
                                            title="Remove label"
                                        >
                                            {label} ×
                                        </button>
                                    ))}
                                    <input
                                        className="kb-tag-input__field"
                                        data-cy="task-labels"
                                        value={labelDraft}
                                        onChange={(e) => setLabelDraft(e.target.value)}
                                        onKeyDown={handleLabelKeyDown}
                                        disabled={!canEditAllFields}
                                        placeholder={form.labels.length ? "Add another label" : "frontend, urgent, bug"}
                                    />
                                </div>
                            </div>
                        </label>
                    </div>

                    <div className="kb-modal-footer">
                        <button className="kb-btn kb-btn--ghost" data-cy="task-cancel" onClick={onClose} type="button">Cancel</button>
                        <button className="kb-btn kb-btn--primary" data-cy="task-save" onClick={handleSubmit} disabled={saving} type="button">
                            {saving ? "Saving…" : isNew ? "Create" : "Save"}
                        </button>
                    </div>
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
    const [priorities, setPriorities] = useState([]);
    const [projects, setProjects] = useState([]);
    const [workspaces, setWorkspaces] = useState([]);
    const [workspaceRefreshToken, setWorkspaceRefreshToken] = useState(0);
    const [internalProjectFilter, setInternalProjectFilter] = useState("");
    const projectFilter =
        onProjectFilterChange !== undefined ? (projectFilterProp ?? "") : internalProjectFilter;
    const setProjectFilter = onProjectFilterChange ?? setInternalProjectFilter;
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editingTask, setEditingTask] = useState(undefined); // undefined = closed, null = new
    const [viewingTask, setViewingTask] = useState(null);
    const [activeWorkspaceId, setActiveWorkspaceId] = useState(() => localStorage.getItem("active_workspace_id") || "");
    const [activeOrganizationId, setActiveOrganizationId] = useState(() => localStorage.getItem("active_organization_id") || "");
    const [taskAssigneeFilter, setTaskAssigneeFilter] = useState("");
    const abortRef = useRef(null);
    const { activeOrganization } = useOrganization();
    const { user, isManagerOrAbove, isManagerOrAboveInWorkspace } = useRole();
    const resolvedOrganizationId = activeOrganization?.id || activeOrganizationId;

    useEffect(() => {
        const syncWorkspace = () => {
            setActiveWorkspaceId(localStorage.getItem("active_workspace_id") || "");
            setWorkspaceRefreshToken((value) => value + 1);
        };
        const syncOrganization = () => {
            setActiveOrganizationId(localStorage.getItem("active_organization_id") || "");
            setWorkspaceRefreshToken((value) => value + 1);
        };
        window.addEventListener("workspace:changed", syncWorkspace);
        window.addEventListener("organization:changed", syncOrganization);
        window.addEventListener("storage", syncWorkspace);
        window.addEventListener("storage", syncOrganization);
        syncWorkspace();
        syncOrganization();
        return () => {
            window.removeEventListener("workspace:changed", syncWorkspace);
            window.removeEventListener("organization:changed", syncOrganization);
            window.removeEventListener("storage", syncWorkspace);
            window.removeEventListener("storage", syncOrganization);
        };
    }, []);
    const projectNameById = useMemo(() => {
        const map = new Map();
        projects.forEach((p) => map.set(p.id, p.name));
        return map;
    }, [projects]);
    const projectById = useMemo(() => {
        const map = new Map();
        projects.forEach((project) => map.set(String(project.id), project));
        return map;
    }, [projects]);
    const selectedProjectForFilter = projectFilter ? projectById.get(String(projectFilter)) : null;
    const canManageProject = useCallback(
        (project) => {
            if (!project) return false;
            if (project.workspace) {
                return isManagerOrAboveInWorkspace(project.workspace);
            }
            return isManagerOrAbove();
        },
        [isManagerOrAbove, isManagerOrAboveInWorkspace]
    );
    const manageableProjects = useMemo(
        () => projects.filter((project) => canManageProject(project)),
        [canManageProject, projects]
    );
    const taskProject = useCallback(
        (task) => projectById.get(String(task?.project?.id ?? task?.project ?? "")),
        [projectById]
    );
    const canManageTask = useCallback(
        (task) => {
            const project = taskProject(task);
            return canManageProject(project);
        },
        [canManageProject, taskProject]
    );
    const canCreateTask = projectFilter
        ? canManageProject(selectedProjectForFilter)
        : manageableProjects.length > 0;
    const canChangeTaskStatus = useCallback(
        (task) => canManageTask(task) || String(task?.assigned_to || "") === String(user?.id || ""),
        [canManageTask, user?.id]
    );

    const canEditTask = useCallback(
        (task) => canManageTask(task) || String(task?.assigned_to || "") === String(user?.id || ""),
        [canManageTask, user?.id]
    );

    const showProjectOnCards = !projectFilter;

    useEffect(() => {
        let cancelled = false;

        const loadWorkspaces = async () => {
            try {
                const accessToken = localStorage.getItem("access");
                let data = [];

                if (resolvedOrganizationId) {
                    try {
                        const orgResponse = await axios.get(
                            `${API.defaults.baseURL}/organizations/${resolvedOrganizationId}/workspaces/`,
                            {
                                signal: abortRef.current?.signal,
                                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
                            }
                        );
                        data = Array.isArray(orgResponse.data) ? orgResponse.data : orgResponse.data?.results ?? [];
                    } catch {
                        data = [];
                    }
                }

                if (!data.length) {
                    const response = await axios.get(
                        `${API.defaults.baseURL}/workspaces/`,
                        {
                            signal: abortRef.current?.signal,
                            headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
                        }
                    );
                    data = Array.isArray(response.data) ? response.data : response.data?.results ?? [];
                }

                if (!cancelled) {
                    setWorkspaces(data);
                }
            } catch {
                if (!cancelled) {
                    setWorkspaces([]);
                }
            }
        };

        loadWorkspaces();
        return () => {
            cancelled = true;
        };
    }, [resolvedOrganizationId, workspaceRefreshToken]);

    useEffect(() => {
        if (!workspaces.length) return;
        const stillValid = workspaces.some((workspace) => String(workspace.id) === String(activeWorkspaceId));
        if (stillValid) return;

        const fallbackWorkspace = workspaces[0];
        if (fallbackWorkspace?.id) {
            setActiveWorkspaceId(String(fallbackWorkspace.id));
            localStorage.setItem("active_workspace_id", String(fallbackWorkspace.id));
            window.dispatchEvent(new CustomEvent("workspace:changed", { detail: { workspaceId: fallbackWorkspace.id } }));
        }
    }, [activeWorkspaceId, workspaces]);

    const assigneeFilterOptions = useMemo(() => {
        const seen = new Set();
        const options = [];

        tasks.forEach((task) => {
            if (!task.assigned_to) return;
            const value = String(task.assigned_to);
            if (seen.has(value)) return;
            seen.add(value);
            options.push({
                value,
                label: task.assigned_to_email || `User ${value}`,
            });
        });

        return options;
    }, [tasks]);

    // ── fetch ──────────────────────────────────────────────────────────────

    const fetchAll = useCallback(async () => {
        if (abortRef.current) abortRef.current.abort();
        abortRef.current = new AbortController();
        setLoading(true);
        setError(null);
        try {
            const taskParams = projectFilter ? { project: projectFilter } : {};
            const [taskList, statusList, priorityList, projectRes] = await Promise.all([
                getTasks(taskParams, abortRef.current.signal),
                getTaskStatuses(abortRef.current.signal),
                getTaskPriorities(abortRef.current.signal),
                API.get("/projects/", { signal: abortRef.current.signal }),
            ]);
            const projectList = Array.isArray(projectRes.data)
                ? projectRes.data
                : projectRes.data.results ?? [];

            setTasks(taskList);
            setStatuses(statusList);
            setPriorities(priorityList);
            setProjects(projectList);
        } catch (err) {
            if (err.name === "CanceledError" || err.name === "AbortError") return;
            setError(getApiErrorMessage(err, "Failed to load board."));
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
        if (!canChangeTaskStatus(previous)) return;
        setTasks((prev) =>
            prev.map((t) => (t.id === taskId ? { ...t, status: newStatusId } : t))
        );
        try {
            const saved = await updateTask(taskId, { status: newStatusId });
            setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, ...saved } : t)));
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
    }, [canChangeTaskStatus, fetchAll, onTasksChanged, tasks]);

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

    const handleDelete = useCallback(async (task) => {
        await deleteTask(task.id);
        setTasks((current) => current.filter((item) => item.id !== task.id));
        if (viewingTask?.id === task.id) {
            setViewingTask(null);
        }
        onTasksChanged?.();
    }, [onTasksChanged, viewingTask]);

    const visibleTasks = useMemo(() => {
        let filtered = tasks;

        if (projectFilter) {
            filtered = filtered.filter((t) => String(t.project) === String(projectFilter));
        }

        if (taskAssigneeFilter === "mine") {
            filtered = filtered.filter((t) => String(t.assigned_to || "") === String(user?.id || ""));
        } else if (taskAssigneeFilter) {
            filtered = filtered.filter((t) => String(t.assigned_to || "") === String(taskAssigneeFilter));
        }

        return filtered;
    }, [projectFilter, taskAssigneeFilter, tasks, user?.id]);

    const grouped = groupByStatus(visibleTasks, statuses);
    const canDropTasks = visibleTasks.some((task) => canChangeTaskStatus(task));

    // ── render ─────────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="kb-state kb-state--loading" data-cy="kanban-loading">
                <LoadingSpinner label="Loading board" />
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
                <div className="kb-header__intro">
                    <h2 className="kb-header__title" data-cy="kanban-title">
                        Task board
                    </h2>
                    <p className="kb-header__desc">
                        Tasks from accessible projects grouped by status.
                    </p>
                </div>
                <div className="kb-header__controls">
                    <label className="kb-filter">
                        <span className="kb-filter-label">Workspace</span>
                        <select
                            className="kb-filter-select"
                            data-cy="kanban-workspace-filter"
                            value={activeWorkspaceId}
                            onChange={(e) => {
                                const workspaceId = e.target.value;
                                setActiveWorkspaceId(workspaceId);
                                if (workspaceId) {
                                    localStorage.setItem("active_workspace_id", workspaceId);
                                } else {
                                    localStorage.removeItem("active_workspace_id");
                                }
                                window.dispatchEvent(new CustomEvent("workspace:changed", { detail: { workspaceId } }));
                            }}
                            aria-label="Select workspace"
                        >
                            <option value="">All accessible workspaces</option>
                            {workspaces.map((workspace) => (
                                <option key={workspace.id} value={String(workspace.id)}>
                                    {workspace.name}
                                </option>
                            ))}
                        </select>
                    </label>
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
                    <label className="kb-filter">
                        <span className="kb-filter-label">Assignee</span>
                        <select
                            className="kb-filter-select"
                            data-cy="kanban-assignee-filter"
                            value={taskAssigneeFilter}
                            onChange={(e) => setTaskAssigneeFilter(e.target.value)}
                            aria-label="Filter tasks by assignee"
                        >
                            <option value="">All assignees</option>
                            <option value="mine">My tasks</option>
                            {assigneeFilterOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    {canCreateTask && (
                        <button
                            className="kb-btn kb-btn--primary"
                            data-cy="new-task-button"
                            onClick={() => setEditingTask(null)}
                            type="button"
                                disabled={manageableProjects.length === 0}
                        >
                            + Add task
                        </button>
                    )}
                </div>
            </header>

            {statuses.length === 0 ? (
                <EmptyState
                    icon="S"
                    title="Task board is not set up"
                    description="Task statuses are unavailable. Contact an administrator."
                    className="kb-state kb-state--empty"
                />
            ) : visibleTasks.length === 0 ? (
                <EmptyState
                    icon="T"
                    title="No tasks yet"
                    description={
                        canCreateTask
                            ? "Create the first task for the selected project or workspace."
                            : "Tasks will appear here when they are created in projects you can access."
                    }
                    actionLabel={canCreateTask ? "Add task" : undefined}
                    onAction={canCreateTask ? () => setEditingTask(null) : undefined}
                    className="kb-state kb-state--empty"
                />
            ) : (
                <div className="kb-board-scroll">
                    <div className="kb-board">
                        {statuses.map((s) => (
                            <Column
                                key={s.id}
                                status={s}
                                tasks={grouped[s.id] ?? []}
                                statuses={statuses}
                                onStatusChange={handleStatusChange}
                                onEdit={(t) => {
                                    if (canEditTask(t)) setEditingTask(t);
                                }}
                                onView={(t) => setViewingTask(t)}
                                onDrop={handleStatusChange}
                                projectNameById={projectNameById}
                                showProject={showProjectOnCards}
                                canMoveTask={canChangeTaskStatus}
                                canDropTasks={canDropTasks}
                                canEditTask={canEditTask}
                            />
                        ))}
                    </div>
                </div>
            )}

            {viewingTask && (
                <TaskDetailModal
                    task={viewingTask}
                    statuses={statuses}
                    priorities={priorities}
                    onClose={() => setViewingTask(null)}
                    onEdit={(t) => {
                        setViewingTask(null);
                        if (canEditTask(t)) setEditingTask(t);
                    }}
                    onDeleted={handleDelete}
                    canDeleteTask={canManageTask(viewingTask) || String(viewingTask.created_by_id || "") === String(user?.id || "")}
                    canEditTask={canEditTask(viewingTask)}
                    canManageAttachments={canManageTask(viewingTask)}
                    canUploadAttachments={canEditTask(viewingTask)}
                    currentUserId={user?.id}
                />
            )}

            {editingTask !== undefined && (editingTask === null ? canCreateTask : canEditTask(editingTask)) && (
                <TaskModal
                    task={editingTask}
                    statuses={statuses}
                    priorities={priorities}
                    projects={editingTask === null || canManageTask(editingTask) ? manageableProjects : projects}
                    workspaceId={selectedProjectForFilter?.workspace || activeWorkspaceId}
                    organizationId={resolvedOrganizationId}
                    canEditAllFields={editingTask === null ? canCreateTask : canManageTask(editingTask)}
                    onClose={() => setEditingTask(undefined)}
                    onSaved={handleSaved}
                    defaultProjectId={projectFilter ? Number(projectFilter) : undefined}
                />
            )}
        </div>
    );
}

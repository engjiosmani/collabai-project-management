import { useEffect, useState } from "react";
import API, { getApiErrorMessage } from "../api/api";
import { getOrganizationMembers } from "../api/organizations";
import {
    addProjectMember,
    createProject,
    fetchProjectMembers,
    removeProjectMember,
    updateProject,
} from "../api/projects";

const getTodayDateInputValue = () => {
    const now = new Date();
    const offsetDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return offsetDate.toISOString().slice(0, 10);
};

const validateProjectDates = ({ start_date, due_date }) => {
    const errors = {};
    const today = getTodayDateInputValue();

    if (start_date && start_date < today) {
        errors.start_date = "Start date cannot be in the past.";
    }

    if (due_date && due_date < today) {
        errors.due_date = "Due date cannot be in the past.";
    } else if (start_date && due_date && due_date < start_date) {
        errors.due_date = "Due date cannot be earlier than start date.";
    }

    return errors;
};

/**
 * Modal for creating or editing a project.
 * Props:
 *   open         {boolean}
 *   project      {object|null}  — null for create, existing project for edit
 *   onClose      {() => void}
 *   onSaved      {(project) => void}
 *   context      {"global"|"workspace"}  — "workspace" hides org/ws selectors
 *   preselectOrg {object} — { id, name } for workspace-context create
 *   preselectWs  {object} — { id, name } for workspace-context create
 */
export default function ProjectFormModal({ open, project, onClose, onSaved, context = "global", preselectOrg, preselectWs }) {
    const isEdit = Boolean(project);
    const projectOrganizationId = project?.organization?.id ?? project?.organization ?? "";
    const isWorkspaceContext = !isEdit && context === "workspace";
    const wsOrgName = preselectOrg?.name || "";
    const wsName = preselectWs?.name || "";

    const [organizations, setOrganizations] = useState([]);
    const [form, setForm] = useState({
        name: "",
        description: "",
        organization: "",
        workspace: "",
        start_date: "",
        due_date: "",
        is_active: true,
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [fieldErrors, setFieldErrors] = useState({});
    const [members, setMembers] = useState([]);
    const [organizationMembers, setOrganizationMembers] = useState([]);
    const [memberError, setMemberError] = useState(null);
    const [memberLoading, setMemberLoading] = useState(false);
    const [memberSaving, setMemberSaving] = useState(false);
    const [selectedMemberId, setSelectedMemberId] = useState("");
    const [workspaces, setWorkspaces] = useState([]);
    const [workspacesLoading, setWorkspacesLoading] = useState(false);
    const today = getTodayDateInputValue();

    // Load organizations for the selector (skip in workspace context)
    useEffect(() => {
        if (!open || isWorkspaceContext) return;
        API.get("/organizations/")
            .then((res) => {
                const list = Array.isArray(res.data)
                    ? res.data
                    : res.data.results ?? [];
                setOrganizations(list);
            })
            .catch(() => {});
    }, [open, isWorkspaceContext]);

    // Load workspaces when organization changes (skip in workspace context)
    useEffect(() => {
        if (!open || isEdit || !form.organization || isWorkspaceContext) {
            setWorkspaces([]);
            return;
        }
        setForm((prev) => ({ ...prev, workspace: "" }));
        setWorkspacesLoading(true);
        API.get(`/organizations/${form.organization}/workspaces/`)
            .then((res) => {
                const list = Array.isArray(res.data) ? res.data : res.data.results ?? [];
                setWorkspaces(list);
                if (list.length === 1) {
                    setForm((prev) => ({ ...prev, workspace: list[0].id }));
                }
            })
            .catch(() => setWorkspaces([]))
            .finally(() => setWorkspacesLoading(false));
    }, [open, isEdit, form.organization, isWorkspaceContext]);

    // Populate form when editing
    useEffect(() => {
        if (!open) return;
        if (project) {
            setForm({
                name: project.name || "",
                description: project.description || "",
                organization: projectOrganizationId || "",
                workspace: project.workspace || "",
                start_date: project.start_date || "",
                due_date: project.due_date || "",
                is_active: project.is_active !== false,
            });
        } else if (isWorkspaceContext && preselectOrg && preselectWs) {
            setForm({
                name: "",
                description: "",
                organization: String(preselectOrg.id),
                workspace: String(preselectWs.id),
                start_date: "",
                due_date: "",
                is_active: true,
            });
        } else {
            setForm({
                name: "",
                description: "",
                organization: organizations[0]?.id || "",
                workspace: "",
                start_date: "",
                due_date: "",
                is_active: true,
            });
        }
        setError(null);
        setFieldErrors({});
    }, [open, project, organizations, projectOrganizationId, isWorkspaceContext, preselectOrg, preselectWs]);

    useEffect(() => {
        if (!open || !isEdit || !projectOrganizationId) {
            setMembers([]);
            setOrganizationMembers([]);
            setSelectedMemberId("");
            setMemberError(null);
            setMemberLoading(false);
            return;
        }

        let active = true;

        const loadMembers = async () => {
            setMemberLoading(true);
            setMemberError(null);

            try {
                const [projectMembers, orgMembers] = await Promise.all([
                    fetchProjectMembers(project.id),
                    getOrganizationMembers(projectOrganizationId),
                ]);

                if (!active) return;

                setMembers(projectMembers);
                setOrganizationMembers(orgMembers);
            } catch (err) {
                if (!active) return;
                setMemberError(getApiErrorMessage(err, "Failed to load project members."));
            } finally {
                if (active) {
                    setMemberLoading(false);
                }
            }
        };

        loadMembers();

        return () => {
            active = false;
        };
    }, [open, isEdit, project?.id, projectOrganizationId]);

    if (!open) return null;

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setForm((prev) => ({
            ...prev,
            [name]: type === "checkbox" ? checked : value,
        }));
        if (name === "organization") {
            setForm((prev) => ({ ...prev, workspace: "" }));
        }
        setFieldErrors((prev) => {
            const next = { ...prev, [name]: undefined };
            if (name === "start_date" || name === "due_date") {
                next.start_date = undefined;
                next.due_date = undefined;
            }
            return next;
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setFieldErrors({});

        const dateErrors = validateProjectDates(form);
        if (Object.keys(dateErrors).length > 0) {
            setFieldErrors(dateErrors);
            return;
        }

        const payload = {
            name: form.name.trim(),
            description: form.description.trim(),
            organization: Number(form.organization),
            workspace: Number(form.workspace),
            is_active: form.is_active,
        };
        if (form.start_date) payload.start_date = form.start_date;
        if (form.due_date) payload.due_date = form.due_date;

        setSaving(true);
        try {
            const saved = isEdit
                ? await updateProject(project.id, payload)
                : await createProject(payload);
            onSaved(saved);
            onClose();
        } catch (err) {
            const data = err?.response?.data;
            if (data && typeof data === "object" && !data.detail) {
                setFieldErrors(data);
            } else {
                setError(getApiErrorMessage(err, "Failed to save project."));
            }
        } finally {
            setSaving(false);
        }
    };

    const projectMemberIds = new Set(members.map((member) => String(member.user)));
    const availableOrganizationMembers = organizationMembers.filter(
        (member) => !projectMemberIds.has(String(member.user_id))
    );

    const displayMemberName = (member) =>
        member.user_full_name ||
        member.user_username ||
        member.username ||
        member.user_email ||
        member.email ||
        `User #${member.user_id ?? member.user}`;

    const handleAddMember = async () => {
        if (!selectedMemberId || !project) return;
        setMemberSaving(true);
        setMemberError(null);

        try {
            const added = await addProjectMember(project.id, Number(selectedMemberId));
            setMembers((prev) => [...prev, added]);
            setSelectedMemberId("");
        } catch (err) {
            setMemberError(getApiErrorMessage(err, "Could not add project member."));
        } finally {
            setMemberSaving(false);
        }
    };

    const handleRemoveMember = async (userId) => {
        if (!project) return;
        setMemberSaving(true);
        setMemberError(null);

        try {
            await removeProjectMember(project.id, userId);
            setMembers((prev) => prev.filter((member) => member.user !== userId));
        } catch (err) {
            setMemberError(getApiErrorMessage(err, "Could not remove project member."));
        } finally {
            setMemberSaving(false);
        }
    };

    return (
        <div className="pm-overlay" role="dialog" aria-modal="true">
            <div className="pm-dialog">
                <div className="pm-header">
                    <h2 className="pm-title">
                        {isEdit ? "Edit Project" : "Create Project"}
                    </h2>
                    <button
                        type="button"
                        className="pm-close"
                        onClick={onClose}
                        aria-label="Close"
                    >
                        ×
                    </button>
                </div>

                {error && (
                    <div className="pm-error" role="alert">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="pm-form">
                    <div className="pm-field">
                        <label className="pm-label" htmlFor="pm-name">
                            Project Name <span className="pm-required">*</span>
                        </label>
                        <input
                            id="pm-name"
                            name="name"
                            type="text"
                            className={`pm-input${fieldErrors.name ? " pm-input--error" : ""}`}
                            value={form.name}
                            onChange={handleChange}
                            required
                            maxLength={150}
                            placeholder="e.g. Website Redesign"
                        />
                        {fieldErrors.name && (
                            <span className="pm-field-error">{fieldErrors.name}</span>
                        )}
                    </div>

                    <div className="pm-field">
                        <label className="pm-label" htmlFor="pm-description">
                            Description
                        </label>
                        <textarea
                            id="pm-description"
                            name="description"
                            className="pm-textarea"
                            value={form.description}
                            onChange={handleChange}
                            rows={3}
                            placeholder="Brief description of the project…"
                        />
                    </div>

                    {isWorkspaceContext ? (
                        <div className="pm-field pm-context-banner">
                            <p className="pm-context-label">
                                Creating project in: <strong>{wsOrgName}</strong> / <strong>{wsName}</strong>
                            </p>
                        </div>
                    ) : (
                        <>
                            <div className="pm-field">
                                <label className="pm-label" htmlFor="pm-org">
                                    Organization <span className="pm-required">*</span>
                                </label>
                                <select
                                    id="pm-org"
                                    name="organization"
                                    className={`pm-select${fieldErrors.organization ? " pm-input--error" : ""}`}
                                    value={form.organization}
                                    onChange={handleChange}
                                    required
                                    disabled={isEdit}
                                >
                                    <option value="">— Select organization —</option>
                                    {organizations.map((org) => (
                                        <option key={org.id} value={org.id}>
                                            {org.name}
                                        </option>
                                    ))}
                                </select>
                                {isEdit && (
                                    <span className="pm-field-hint">
                                        Organization cannot be changed after creation.
                                    </span>
                                )}
                                {fieldErrors.organization && (
                                    <span className="pm-field-error">
                                        {fieldErrors.organization}
                                    </span>
                                )}
                            </div>

                            {!isEdit && (
                                <div className="pm-field">
                                    <label className="pm-label" htmlFor="pm-workspace">
                                        Workspace <span className="pm-required">*</span>
                                    </label>
                                    {workspacesLoading ? (
                                        <p className="pm-field-hint">Loading workspaces…</p>
                                    ) : form.organization && workspaces.length === 0 ? (
                                        <div className="pm-workspace-empty">
                                            <p className="pm-field-hint">
                                                No workspaces found for this organization.
                                            </p>
                                            <a
                                                href={`/organizations/${form.organization}`}
                                                className="dashboard-button dashboard-button--ghost"
                                                style={{ display: "inline-block", marginTop: "8px", fontSize: "13px", padding: "6px 12px" }}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                Create workspace
                                            </a>
                                        </div>
                                    ) : (
                                        <select
                                            id="pm-workspace"
                                            name="workspace"
                                            className={`pm-select${fieldErrors.workspace ? " pm-input--error" : ""}`}
                                            value={form.workspace}
                                            onChange={handleChange}
                                            required
                                            disabled={!form.organization || workspaces.length === 0}
                                        >
                                            <option value="">
                                                {form.organization
                                                    ? "— Select workspace —"
                                                    : "— Select an organization first —"}
                                            </option>
                                            {workspaces.map((ws) => (
                                                <option key={ws.id} value={ws.id}>
                                                    {ws.name}
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                    {fieldErrors.workspace && (
                                        <span className="pm-field-error">
                                            {fieldErrors.workspace}
                                        </span>
                                    )}
                                </div>
                            )}
                        </>
                    )}

                    <div className="pm-row">
                        <div className="pm-field">
                            <label className="pm-label" htmlFor="pm-start">
                                Start Date
                            </label>
                            <input
                                id="pm-start"
                                name="start_date"
                                type="date"
                                className={`pm-input${fieldErrors.start_date ? " pm-input--error" : ""}`}
                                value={form.start_date}
                                onChange={handleChange}
                                min={today}
                                aria-describedby={fieldErrors.start_date ? "pm-start-error" : undefined}
                            />
                            {fieldErrors.start_date && (
                                <span id="pm-start-error" className="pm-field-error">
                                    {fieldErrors.start_date}
                                </span>
                            )}
                        </div>
                        <div className="pm-field">
                            <label className="pm-label" htmlFor="pm-due">
                                Due Date
                            </label>
                            <input
                                id="pm-due"
                                name="due_date"
                                type="date"
                                className={`pm-input${fieldErrors.due_date ? " pm-input--error" : ""}`}
                                value={form.due_date}
                                onChange={handleChange}
                                min={form.start_date || today}
                                aria-describedby={fieldErrors.due_date ? "pm-due-error" : undefined}
                            />
                            {fieldErrors.due_date && (
                                <span id="pm-due-error" className="pm-field-error">
                                    {fieldErrors.due_date}
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="pm-field pm-field--checkbox">
                        <label className="pm-checkbox-label">
                            <input
                                name="is_active"
                                type="checkbox"
                                checked={form.is_active}
                                onChange={handleChange}
                            />
                            Active project
                        </label>
                    </div>

                    {isEdit && (
                        <section className="pm-section">
                            <div className="pm-section-head">
                                <div>
                                    <h3 className="pm-section-title">Project members</h3>
                                    <p className="pm-section-subtitle">
                                        Add organization members to this project and remove access when needed.
                                    </p>
                                </div>
                                <span className="pm-section-pill">
                                    {members.length} member{members.length === 1 ? "" : "s"}
                                </span>
                            </div>

                            {memberError && (
                                <div className="pm-error" role="alert">
                                    {memberError}
                                </div>
                            )}

                            <div className="pm-add-member">
                                <select
                                    className="pm-select"
                                    value={selectedMemberId}
                                    onChange={(e) => setSelectedMemberId(e.target.value)}
                                    disabled={memberSaving || availableOrganizationMembers.length === 0}
                                >
                                    <option value="">— Add a project member —</option>
                                    {availableOrganizationMembers.map((member) => (
                                        <option key={member.id} value={member.user_id}>
                                            {displayMemberName(member)}
                                            {member.job_role_name ? ` · ${member.job_role_name}` : ""}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="dashboard-button dashboard-button--primary"
                                    onClick={handleAddMember}
                                    disabled={
                                        memberSaving ||
                                        !selectedMemberId ||
                                        availableOrganizationMembers.length === 0
                                    }
                                >
                                    {memberSaving ? "Adding…" : "Add member"}
                                </button>
                            </div>

                            {memberLoading ? (
                                <p className="pm-muted">Loading members…</p>
                            ) : members.length === 0 ? (
                                <p className="pm-muted">
                                    No members yet. Add organization members to share this project.
                                </p>
                            ) : (
                                <ul className="pm-member-list">
                                    {members.map((member) => (
                                        <li key={member.id} className="pm-member-item">
                                            <div className="pm-member-avatar">
                                                {(displayMemberName(member)[0] || "?").toUpperCase()}
                                            </div>
                                            <div className="pm-member-info">
                                                <span className="pm-member-name">
                                                    {displayMemberName(member)}
                                                </span>
                                                <span className="pm-member-email">
                                                    {member.user_email || member.email || ""}
                                                </span>
                                            </div>
                                            <button
                                                type="button"
                                                className="pm-member-remove"
                                                onClick={() => handleRemoveMember(member.user)}
                                                disabled={memberSaving}
                                                title="Remove member"
                                            >
                                                ×
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </section>
                    )}

                    <div className="pm-actions">
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--ghost"
                            onClick={onClose}
                            disabled={saving}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="dashboard-button dashboard-button--primary"
                            disabled={saving || !form.name.trim() || !form.organization || (!isEdit && !form.workspace)}
                        >
                            {saving
                                ? isEdit
                                    ? "Saving…"
                                    : "Creating…"
                                : isEdit
                                ? "Save changes"
                                : "Create project"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

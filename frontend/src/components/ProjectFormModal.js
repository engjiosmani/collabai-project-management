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

/**
 * Modal for creating or editing a project.
 * Props:
 *   open         {boolean}
 *   project      {object|null}  — null for create, existing project for edit
 *   onClose      {() => void}
 *   onSaved      {(project) => void}
 */
export default function ProjectFormModal({ open, project, onClose, onSaved }) {
    const isEdit = Boolean(project);
    const projectOrganizationId = project?.organization?.id ?? project?.organization ?? "";

    const [organizations, setOrganizations] = useState([]);
    const [form, setForm] = useState({
        name: "",
        description: "",
        organization: "",
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

    // Load organizations for the selector
    useEffect(() => {
        if (!open) return;
        API.get("/organizations/")
            .then((res) => {
                const list = Array.isArray(res.data)
                    ? res.data
                    : res.data.results ?? [];
                setOrganizations(list);
            })
            .catch(() => {});
    }, [open]);

    // Populate form when editing
    useEffect(() => {
        if (!open) return;
        if (project) {
            setForm({
                name: project.name || "",
                description: project.description || "",
                organization: projectOrganizationId || "",
                start_date: project.start_date || "",
                due_date: project.due_date || "",
                is_active: project.is_active !== false,
            });
        } else {
            setForm({
                name: "",
                description: "",
                organization: organizations[0]?.id || "",
                start_date: "",
                due_date: "",
                is_active: true,
            });
        }
        setError(null);
        setFieldErrors({});
    }, [open, project, organizations, projectOrganizationId]);

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
        setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setFieldErrors({});

        const payload = {
            name: form.name.trim(),
            description: form.description.trim(),
            organization: Number(form.organization),
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

                    <div className="pm-row">
                        <div className="pm-field">
                            <label className="pm-label" htmlFor="pm-start">
                                Start Date
                            </label>
                            <input
                                id="pm-start"
                                name="start_date"
                                type="date"
                                className="pm-input"
                                value={form.start_date}
                                onChange={handleChange}
                            />
                        </div>
                        <div className="pm-field">
                            <label className="pm-label" htmlFor="pm-due">
                                Due Date
                            </label>
                            <input
                                id="pm-due"
                                name="due_date"
                                type="date"
                                className="pm-input"
                                value={form.due_date}
                                onChange={handleChange}
                            />
                            {fieldErrors.due_date && (
                                <span className="pm-field-error">
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
                            disabled={saving || !form.name.trim() || !form.organization}
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
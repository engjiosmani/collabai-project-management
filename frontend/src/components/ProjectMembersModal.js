import { useCallback, useEffect, useState } from "react";
import { getApiErrorMessage } from "../api/api";
import { getOrganizationMembers } from "../api/organizations";
import {
    addProjectMember,
    fetchProjectMembers,
    removeProjectMember,
} from "../api/projects";

/**
 * Modal for managing project members.
 * Props:
 *   open      {boolean}
 *   project   {object|null}
 *   onClose   {() => void}
 */
export default function ProjectMembersModal({ open, project, onClose }) {
    const organizationId = project?.organization?.id ?? project?.organization ?? null;
    const [members, setMembers] = useState([]);
    const [orgUsers, setOrgUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [adding, setAdding] = useState(false);
    const [selectedUserId, setSelectedUserId] = useState("");
    const [error, setError] = useState(null);

    const loadData = useCallback(async () => {
        if (!project || !organizationId) return;
        setLoading(true);
        setError(null);
        try {
            const [membersData, usersData] = await Promise.all([
                fetchProjectMembers(project.id),
                getOrganizationMembers(organizationId),
            ]);
            setMembers(membersData);
            setOrgUsers(usersData);
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not load members."));
        } finally {
            setLoading(false);
        }
    }, [project, organizationId]);

    useEffect(() => {
        if (open && project) loadData();
    }, [open, project, loadData]);

    if (!open || !project) return null;

    const memberUserIds = new Set(members.map((m) => String(m.user)));
    const availableUsers = orgUsers.filter((u) => !memberUserIds.has(String(u.user_id)));

    const handleAdd = async () => {
        if (!selectedUserId) return;
        setAdding(true);
        setError(null);
        try {
            await addProjectMember(project.id, Number(selectedUserId));
            setSelectedUserId("");
            await loadData();
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not add member."));
        } finally {
            setAdding(false);
        }
    };

    const handleRemove = async (userId) => {
        setError(null);
        try {
            await removeProjectMember(project.id, userId);
            setMembers((prev) => prev.filter((m) => m.user !== userId));
        } catch (err) {
            setError(getApiErrorMessage(err, "Could not remove member."));
        }
    };

    const displayName = (m) =>
        m.user_full_name ||
        m.user_username ||
        m.username ||
        m.user_email ||
        m.email ||
        `User #${m.user_id ?? m.user}`;

    return (
        <div className="pm-overlay" role="dialog" aria-modal="true">
            <div className="pm-dialog pm-dialog--members">
                <div className="pm-header">
                    <h2 className="pm-title">Members — {project.name}</h2>
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

                {/* Add member */}
                {availableUsers.length > 0 && (
                    <div className="pm-add-member">
                        <select
                            className="pm-select"
                            value={selectedUserId}
                            onChange={(e) => setSelectedUserId(e.target.value)}
                        >
                            <option value="">— Add a member —</option>
                            {availableUsers.map((u) => (
                                <option key={u.user_id} value={u.user_id}>
                                    {u.username || u.email || `User #${u.user_id}`}
                                </option>
                            ))}
                        </select>
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--primary"
                            onClick={handleAdd}
                            disabled={adding || !selectedUserId}
                        >
                            {adding ? "Adding…" : "Add"}
                        </button>
                    </div>
                )}

                {/* Members list */}
                {loading ? (
                    <p className="pm-muted">Loading members…</p>
                ) : members.length === 0 ? (
                    <p className="pm-muted">No members yet.</p>
                ) : (
                    <ul className="pm-member-list">
                        {members.map((m) => (
                                <li key={m.id} className="pm-member-item">
                                    <div className="pm-member-avatar">
                                        {(displayName(m)[0] || "?").toUpperCase()}
                                    </div>
                                    <div className="pm-member-info">
                                        <span className="pm-member-name">{displayName(m)}</span>
                                        <span className="pm-member-email">{m.user_email}</span>
                                    </div>
                                    <button
                                        type="button"
                                        className="pm-member-remove"
                                        onClick={() => handleRemove(m.user)}
                                        title="Remove member"
                                    >
                                        ×
                                    </button>
                                </li>
                        ))}
                    </ul>
                )}

                <div className="pm-actions pm-actions--right">
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--ghost"
                        onClick={onClose}
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
}
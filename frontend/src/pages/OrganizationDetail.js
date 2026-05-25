import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";

import {
  createWorkspace,
  deleteOrganization,
  deleteWorkspace,
  getOrganizationMembers,
  getOrganizationWorkspaces,
  getOrganizationInvites,
  inviteOrganizationMember,
  updateOrganizationMember,
  removeOrganizationMember,
  removeOrganizationInvite,
  updateOrganization,
  updateWorkspace,
} from "../api/organizations";
import { getApiErrorMessage } from "../api/api";
import API from "../api/api";
import AppSidebar from "../components/AppSidebar";
import RoleGate from "../components/RoleGate";
import EmptyState from "../components/ui/EmptyState";
import LoadingSkeleton from "../components/ui/LoadingSkeleton";
import { AuthContext } from "../context/AuthContext";
import { useOrganization } from "../context/OrganizationContext";
import "./Dashboard.css";

const ROLE_LABELS = {
  org_admin: "Organization Admin",
  workspace_admin: "Workspace Admin",
  manager: "Manager",
  member: "Member",
};
const ORG_ROLES = [
  { value: "member", label: "Member" },
  { value: "org_admin", label: "Organization Admin" },
];
const INVITE_ROLES = [
  { value: "member", label: "Organization Member" },
  { value: "org_admin", label: "Organization Admin" },
  { value: "workspace_admin", label: "Workspace Admin" },
  { value: "manager", label: "Workspace Manager" },
];
const INVITE_ROLE_HELP = {
  member: "Members can be added to a workspace now or later.",
  org_admin: "Organization admins automatically have access to every workspace.",
  workspace_admin: "Workspace admins manage one selected workspace.",
  manager: "Workspace managers can create and manage projects and tasks in one selected workspace.",
};

export default function OrganizationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, refreshProfile } = useContext(AuthContext);
  const { refreshOrganizations } = useOrganization();
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [tab, setTab] = useState("workspaces");
  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [saving, setSaving] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member", workspace_id: "" });
  const [settingsForm, setSettingsForm] = useState({ name: "", description: "" });

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteWorkspaceId, setDeleteWorkspaceId] = useState(null);
  const [deleteWorkspaceName, setDeleteWorkspaceName] = useState("");
  const [workspaceModal, setWorkspaceModal] = useState(null);
  const [workspaceForm, setWorkspaceForm] = useState({ name: "", description: "", is_active: true });
  const [workspaceSaving, setWorkspaceSaving] = useState(false);

  const clear = () => { setError(""); setSuccess(""); };

  const currentMember = members.find(
    (m) => String(m.user_id) === String(user?.id)
  );
  const isAdmin = currentMember?.role === "org_admin";

  const visibleTabs = useMemo(() => {
    const tabs = [
      ["workspaces", `Workspaces (${workspaces.length})`],
      ["members", `Members (${members.length})`],
    ];
    if (isAdmin) {
      tabs.push(["requests", `Invitations (${invites.length})`]);
      tabs.push(["settings", "Settings"]);
    }
    return tabs;
  }, [isAdmin, invites.length, members.length, workspaces.length]);

  useEffect(() => {
    if (!visibleTabs.some(([v]) => v === tab)) setTab("workspaces");
  }, [tab, visibleTabs]);

  const loadOrg = useCallback(async () => {
    setLoading(true);
    clear();
    try {
      const [orgRes, memberData, inviteData, workspaceData] = await Promise.all([
        API.get(`/organizations/${id}/`),
        getOrganizationMembers(id),
        isAdmin ? getOrganizationInvites(id) : Promise.resolve([]),
        getOrganizationWorkspaces(id),
      ]);
      setOrg(orgRes.data);
      setMembers(memberData);
      setInvites(isAdmin ? inviteData : []);
      setWorkspaces(workspaceData);
      setSettingsForm({ name: orgRes.data.name || "", description: orgRes.data.description || "" });
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load organization."));
    } finally {
      setLoading(false);
    }
  }, [id, isAdmin]);

  useEffect(() => {
    loadOrg();
  }, [loadOrg]);

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSaving(true);
    clear();
    try {
      const updated = await updateOrganization(id, settingsForm);
      setOrg((prev) => ({ ...prev, ...updated }));
      setSuccess("Organization updated.");
      await refreshOrganizations?.();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update organization."));
    } finally {
      setSaving(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteForm.email.trim()) return;
    if (["workspace_admin", "manager"].includes(inviteForm.role) && !inviteForm.workspace_id) return;
    setInviting(true);
    clear();
    try {
      await inviteOrganizationMember(id, {
        email: inviteForm.email.trim(),
        role: inviteForm.role,
        workspace_id: inviteForm.workspace_id ? Number(inviteForm.workspace_id) : null,
      });
      setInviteForm({ email: "", role: "member", workspace_id: "" });
      const newInvites = await getOrganizationInvites(id);
      setInvites(newInvites);
      setSuccess("Invitation sent.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to invite member."));
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveInvite = async (invite) => {
    if (!window.confirm(`Remove invitation for ${invite.email}?`)) return;
    clear();
    try {
      await removeOrganizationInvite(id, invite.id);
      setInvites((prev) => prev.filter((i) => i.id !== invite.id));
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to remove invitation."));
    }
  };

  const handleChangeRole = async (member, role) => {
    clear();
    try {
      await updateOrganizationMember(id, member.user_id, { role });
      const data = await getOrganizationMembers(id);
      setMembers(data);
      setSuccess("Member role updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update role."));
    }
  };

  const handleRemoveMember = async (member) => {
    if (!window.confirm(`Remove ${member.email} from this organization?`)) return;
    clear();
    try {
      await removeOrganizationMember(id, member.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== member.user_id));
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to remove member."));
    }
  };

  const handleDeleteOrg = async () => {
    if (deleteConfirm !== org?.name) return;
    setDeleting(true);
    clear();
    try {
      await deleteOrganization(id);
      await refreshOrganizations?.();
      navigate("/organizations", { state: { deletedOrg: org?.name } });
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete organization."));
      setDeleting(false);
    }
  };

  const handleDeleteWorkspace = async (wsId) => {
    clear();
    try {
      await deleteWorkspace(id, wsId);
      setWorkspaces((prev) => prev.filter((w) => w.id !== wsId));
      setDeleteWorkspaceId(null);
      setDeleteWorkspaceName("");
      setSuccess("Workspace archived.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to archive workspace."));
    }
  };

  const handleOpenCreateWorkspace = () => {
    setWorkspaceForm({ name: "", description: "", is_active: true });
    setWorkspaceModal("create");
  };

  const handleOpenEditWorkspace = (ws) => {
    setWorkspaceForm({ name: ws.name, description: ws.description || "", is_active: ws.is_active });
    setWorkspaceModal(ws);
  };

  const handleSaveWorkspace = async (e) => {
    e.preventDefault();
    if (!workspaceForm.name.trim()) return;
    setWorkspaceSaving(true);
    clear();
    try {
      if (workspaceModal === "create") {
        await createWorkspace(id, workspaceForm);
        setSuccess("Workspace created.");
        await refreshProfile?.();
      } else {
        await updateWorkspace(id, workspaceModal.id, workspaceForm);
        setSuccess("Workspace updated.");
      }
      setWorkspaceModal(null);
      const data = await getOrganizationWorkspaces(id);
      setWorkspaces(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save workspace."));
    } finally {
      setWorkspaceSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <LoadingSkeleton variant="card" count={2} lines={5} label="Loading organization" />
        </main>
      </div>
    );
  }

  if (error && !org) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <EmptyState icon="!" title="Could not load organization" description={error} />
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main">
        <div className="org-detail-top">
          <Link to="/organizations" className="org-detail-back">&larr; All Organizations</Link>
        </div>

        <div className="org-detail-header">
          <div className="org-detail-header-main">
            <p className="org-detail-eyebrow">Organization</p>
            <h1 className="org-detail-name">{org?.name}</h1>
            <p className="org-detail-description">{org?.description || "No description"}</p>
          </div>
          <div className="org-detail-header-actions">
            {currentMember && (
              <span className="org-detail-role-badge">{ROLE_LABELS[currentMember.role] || currentMember.role}</span>
            )}
          </div>
        </div>

        {error && (
          <div className="org-flash-message org-flash-message--error">{error}</div>
        )}
        {success && (
          <div className="org-flash-message org-flash-message--success">{success}</div>
        )}

        <div className="org-detail-tabs">
          {visibleTabs.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`org-detail-tab${tab === value ? " org-detail-tab--active" : ""}`}
              onClick={() => setTab(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "members" && (
          <>
            <RoleGate requiredRole="org_admin">
              <section className="org-detail-section">
                <h3 className="org-detail-section-title">Invite Member</h3>
                <form onSubmit={handleInvite} className="org-invite-form">
                  <input
                    className="org-invite-input"
                    placeholder="member@example.com"
                    value={inviteForm.email}
                    onChange={(e) => setInviteForm((p) => ({ ...p, email: e.target.value }))}
                  />
                  <select
                    className="org-invite-select"
                    value={inviteForm.role}
                    onChange={(e) => {
                      const role = e.target.value;
                      setInviteForm((p) => ({
                        ...p,
                        role,
                        workspace_id: role === "org_admin" ? "" : p.workspace_id,
                      }));
                    }}
                  >
                    {INVITE_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                  {inviteForm.role !== "org_admin" && (
                    <select
                      className="org-invite-select"
                      value={inviteForm.workspace_id}
                      onChange={(e) => setInviteForm((p) => ({ ...p, workspace_id: e.target.value }))}
                      required={["workspace_admin", "manager"].includes(inviteForm.role)}
                    >
                      <option value="">
                        {inviteForm.role === "member" ? "Organization only" : "Select workspace"}
                      </option>
                      {workspaces.map((ws) => (
                        <option key={ws.id} value={ws.id}>{ws.name}</option>
                      ))}
                    </select>
                  )}
                  <button
                    className="dashboard-button dashboard-button--primary"
                    type="submit"
                    disabled={
                      inviting ||
                      !inviteForm.email.trim() ||
                      (["workspace_admin", "manager"].includes(inviteForm.role) && !inviteForm.workspace_id)
                    }
                  >
                    {inviting ? "Inviting..." : "Invite"}
                  </button>
                </form>
                <p className="org-empty-hint" style={{ margin: "8px 0 0", color: "#64748b", fontSize: "13px" }}>
                  {["workspace_admin", "manager"].includes(inviteForm.role) && workspaces.length === 0
                    ? "Create a workspace before inviting someone to a workspace role."
                    : INVITE_ROLE_HELP[inviteForm.role]}
                </p>
              </section>
            </RoleGate>

            <section className="org-detail-section">
              <h3 className="org-detail-section-title">Members</h3>
              {members.length === 0 ? (
                <p className="org-empty-message">No members yet.</p>
              ) : (
                <div className="org-member-list">
                  {members.map((member) => (
                    <div key={member.id} className="org-member-item">
                      <div className="org-member-info">
                        <strong>{member.username || member.email}</strong>
                        <p className="org-member-email">{member.email}</p>
                        <span className="org-member-role-badge">{ROLE_LABELS[member.role] || member.role}</span>
                      </div>
                      {isAdmin && (
                        <div className="org-member-actions">
                          <select
                            className="org-member-role-select"
                            value={member.role}
                            onChange={(e) => handleChangeRole(member, e.target.value)}
                          >
                            {ORG_ROLES.map((r) => (
                              <option key={r.value} value={r.value}>{r.label}</option>
                            ))}
                          </select>
                          <button
                            type="button"
                            className="dashboard-button dashboard-button--danger"
                            style={{ padding: "10px 14px", fontSize: "13px" }}
                            onClick={() => handleRemoveMember(member)}
                          >
                            Remove
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {tab === "requests" && isAdmin && (
          <section className="org-detail-section">
            <h3 className="org-detail-section-title">Pending invitations</h3>
            {invites.length === 0 ? (
              <p className="org-empty-message">No pending invitations.</p>
            ) : (
              <div className="org-invite-list">
                {invites.map((invite) => (
                  <div key={invite.id} className="org-invite-item">
                    <div>
                      <div className="org-invite-email">{invite.email}</div>
                      <p className="org-invite-meta">
                        Role: {ROLE_LABELS[invite.role] || invite.role}
                        {invite.workspace ? ` · ${invite.workspace_name || `Workspace #${invite.workspace}`}` : ""}
                        {" · "}
                        Expires: {invite.expires_at ? new Date(invite.expires_at).toLocaleString() : "Not specified"}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="dashboard-button dashboard-button--danger"
                      style={{ padding: "10px 14px", fontSize: "13px" }}
                      onClick={() => handleRemoveInvite(invite)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "workspaces" && (
          <section className="org-detail-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
              <h3 className="org-detail-section-title" style={{ margin: 0 }}>Workspaces</h3>
              {isAdmin && (
                <button
                  type="button"
                  className="dashboard-button dashboard-button--primary"
                  style={{ padding: "10px 16px", fontSize: "0.85rem" }}
                  onClick={handleOpenCreateWorkspace}
                >
                  Create Workspace
                </button>
              )}
            </div>
            {workspaces.length === 0 ? (
              <div className="org-empty-state">
                <p className="org-empty-message">No workspaces yet.</p>
                <p className="org-empty-hint" style={{ margin: "4px 0 0", color: "#64748b", fontSize: "14px" }}>
                  {isAdmin
                    ? "Create a workspace before adding workspace roles, projects, and tasks."
                    : "Workspaces will appear here when an organization admin creates one."}
                </p>
              </div>
            ) : (
              <div className="org-workspace-list">
                {workspaces.map((ws) => (
                  <div key={ws.id} className="org-workspace-item">
                    <div className="org-workspace-row">
                      <div>
                        <div className="org-workspace-name">{ws.name}</div>
                        {ws.description && (
                          <p style={{ margin: "4px 0 0", color: "#475569", fontSize: "13px", lineHeight: "1.4" }}>{ws.description}</p>
                        )}
                        <p className="org-workspace-meta">
                          {ws.project_count ?? 0} projects &middot; {ws.member_count ?? 0} members &middot; {ws.is_active ? "Active" : "Inactive"}
                        </p>
                      </div>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                        <Link
                          to={`/organizations/${id}/workspaces/${ws.id}`}
                          className="dashboard-button"
                          style={{ padding: "8px 14px", fontSize: "13px", background: "#f1f5f9", color: "#334155", boxShadow: "none", textDecoration: "none" }}
                        >
                          Open
                        </Link>
                        {isAdmin && (
                          <>
                            <button
                              type="button"
                              className="dashboard-button"
                              style={{ padding: "8px 14px", fontSize: "13px", background: "#f1f5f9", color: "#334155", boxShadow: "none" }}
                              onClick={() => handleOpenEditWorkspace(ws)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="dashboard-button dashboard-button--danger"
                              style={{ padding: "8px 14px", fontSize: "13px" }}
                              onClick={() => { setDeleteWorkspaceId(ws.id); setDeleteWorkspaceName(ws.name); }}
                            >
                              Archive
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "settings" && isAdmin && (
          <>
            <section className="org-detail-section">
              <h3 className="org-detail-section-title">Organization Settings</h3>
              <form onSubmit={handleSaveSettings} className="org-settings-form">
                <div className="org-settings-field">
                  <label>Name</label>
                  <input
                    className="org-settings-input"
                    value={settingsForm.name}
                    onChange={(e) => setSettingsForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div className="org-settings-field">
                  <label>Description</label>
                  <textarea
                    className="org-settings-textarea"
                    value={settingsForm.description}
                    onChange={(e) => setSettingsForm((p) => ({ ...p, description: e.target.value }))}
                  />
                </div>
                <button className="dashboard-button dashboard-button--primary" type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save Organization"}
                </button>
              </form>
            </section>

            <section className="org-detail-section org-detail-section--danger">
              <h3 className="org-detail-section-title" style={{ color: "#dc2626" }}>Danger Zone</h3>
              <p className="org-danger-text">
                This will delete the organization and affect its workspaces, projects, tasks, members, and invitations.
              </p>
              <button
                className="dashboard-button dashboard-button--danger"
                type="button"
                onClick={() => { clear(); setDeleteConfirm("init"); }}
              >
                Delete this organization
              </button>
            </section>
          </>
        )}
      </main>

      {deleteConfirm && (
        <div className="org-modal-overlay" onClick={() => { setDeleteConfirm(""); setDeleting(false); }}>
          <div className="org-modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ color: "#dc2626" }}>Delete Organization</h2>
            <p className="org-delete-warning">
              This will delete <strong>{org?.name}</strong> and affect its workspaces, projects, tasks, members, and invitations. This action cannot be undone.
            </p>
            <p className="org-delete-confirm-hint">
              Type <strong>{org?.name}</strong> to confirm:
            </p>
            <input
              className="org-settings-input"
              style={{ marginBottom: "16px" }}
              placeholder={org?.name}
              value={deleteConfirm === "init" ? "" : deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              autoFocus
            />
            <div className="org-modal-actions">
              <button
                type="button"
                className="dashboard-button dashboard-button--ghost"
                onClick={() => { setDeleteConfirm(""); setDeleting(false); }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="dashboard-button dashboard-button--danger"
                disabled={deleteConfirm !== org?.name || deleting}
                onClick={handleDeleteOrg}
              >
                {deleting ? "Deleting..." : "Delete Organization"}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteWorkspaceId && (
        <div className="org-modal-overlay" onClick={() => { setDeleteWorkspaceId(null); setDeleteWorkspaceName(""); }}>
          <div className="org-modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ color: "#dc2626" }}>Archive Workspace</h2>
            <p className="org-delete-warning">
              This will hide <strong>{deleteWorkspaceName}</strong> from active workspace lists and stop new work from being added there.
            </p>
            <div className="org-modal-actions">
              <button
                type="button"
                className="dashboard-button dashboard-button--ghost"
                onClick={() => { setDeleteWorkspaceId(null); setDeleteWorkspaceName(""); }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="dashboard-button dashboard-button--danger"
                onClick={() => handleDeleteWorkspace(deleteWorkspaceId)}
              >
                Archive Workspace
              </button>
            </div>
          </div>
        </div>
      )}

      {workspaceModal && (
        <div className="org-modal-overlay" onClick={() => setWorkspaceModal(null)}>
          <div className="org-modal" onClick={(e) => e.stopPropagation()}>
            <h2>{workspaceModal === "create" ? "Create Workspace" : "Edit Workspace"}</h2>
            <form onSubmit={handleSaveWorkspace}>
              <div className="org-modal-field">
                <label>Workspace name</label>
                <input
                  placeholder="e.g. Engineering"
                  value={workspaceForm.name}
                  onChange={(e) => setWorkspaceForm((p) => ({ ...p, name: e.target.value }))}
                  autoFocus
                />
              </div>
              <div className="org-modal-field">
                <label>Description (optional)</label>
                <textarea
                  placeholder="Brief description of this workspace"
                  value={workspaceForm.description}
                  onChange={(e) => setWorkspaceForm((p) => ({ ...p, description: e.target.value }))}
                />
              </div>
              <div className="org-modal-field" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <input
                  id="ws-is-active"
                  type="checkbox"
                  checked={workspaceForm.is_active}
                  onChange={(e) => setWorkspaceForm((p) => ({ ...p, is_active: e.target.checked }))}
                  style={{ width: "18px", height: "18px" }}
                />
                <label htmlFor="ws-is-active" style={{ margin: 0, fontWeight: 600 }}>Workspace is active</label>
              </div>
              <p className="org-empty-hint" style={{ marginTop: "-8px", color: "#64748b", fontSize: "13px" }}>
                Inactive workspaces are hidden from normal work views.
              </p>
              <div className="org-modal-actions">
                <button
                  type="button"
                  className="dashboard-button dashboard-button--ghost"
                  onClick={() => setWorkspaceModal(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="dashboard-button dashboard-button--primary"
                  disabled={workspaceSaving || !workspaceForm.name.trim()}
                >
                  {workspaceSaving ? "Saving..." : workspaceModal === "create" ? "Create Workspace" : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

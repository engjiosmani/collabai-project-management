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

export default function OrganizationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const { refreshOrganizations } = useOrganization();
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [tab, setTab] = useState("overview");
  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [saving, setSaving] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member" });
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
      ["overview", "Overview"],
      ["members", "Members"],
      ["workspaces", "Workspaces"],
    ];
    if (isAdmin) {
      tabs.push(["requests", `Requests (${invites.length})`]);
      tabs.push(["settings", "Settings"]);
    }
    return tabs;
  }, [isAdmin, invites.length]);

  useEffect(() => {
    if (!visibleTabs.some(([v]) => v === tab)) setTab("overview");
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
    setInviting(true);
    clear();
    try {
      await inviteOrganizationMember(id, {
        email: inviteForm.email.trim(),
        role: inviteForm.role,
      });
      setInviteForm({ email: "", role: "member" });
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
      setSuccess("Workspace deleted.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete workspace."));
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

        {tab === "overview" && (
          <div className="orgs-overview-grid">
            <section className="orgs-overview-card">
              <h3>Members</h3>
              <p className="orgs-overview-stat">{org?.member_count ?? members.length}</p>
              <p className="orgs-overview-hint">Total members in this organization</p>
            </section>
            <section className="orgs-overview-card">
              <h3>Workspaces</h3>
              <p className="orgs-overview-stat">{workspaces.length}</p>
              <p className="orgs-overview-hint">Workspaces across this organization</p>
            </section>
            <section className="orgs-overview-card">
              <h3>Your role</h3>
              <p className="orgs-overview-stat orgs-overview-stat--role">
                {currentMember ? ROLE_LABELS[currentMember.role] || currentMember.role : "Member"}
              </p>
              <p className="orgs-overview-hint">
                {isAdmin ? "You can manage members, settings, and workspaces" : "View organization content and collaborate"}
              </p>
            </section>
          </div>
        )}

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
                    onChange={(e) => setInviteForm((p) => ({ ...p, role: e.target.value }))}
                  >
                    {ORG_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                  <button className="dashboard-button dashboard-button--primary" type="submit" disabled={inviting}>
                    {inviting ? "Inviting..." : "Invite"}
                  </button>
                </form>
              </section>
            </RoleGate>

            <section className="org-detail-section">
              <h3 className="org-detail-section-title">Members ({members.length})</h3>
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
            <h3 className="org-detail-section-title">Pending Requests ({invites.length})</h3>
            {invites.length === 0 ? (
              <p className="org-empty-message">No pending invitation requests.</p>
            ) : (
              <div className="org-invite-list">
                {invites.map((invite) => (
                  <div key={invite.id} className="org-invite-item">
                    <div>
                      <div className="org-invite-email">{invite.email}</div>
                      <p className="org-invite-meta">Role: {invite.role} &middot; Expires: {invite.expires_at ? new Date(invite.expires_at).toLocaleString() : "Not specified"}</p>
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
              <h3 className="org-detail-section-title" style={{ margin: 0 }}>Workspaces ({workspaces.length})</h3>
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
              <p className="org-empty-message">No workspaces yet.</p>
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
                              Delete
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
            <h2 style={{ color: "#dc2626" }}>Delete Workspace</h2>
            <p className="org-delete-warning">
              This will delete <strong>{deleteWorkspaceName}</strong> and affect its projects and tasks. This action cannot be undone.
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
                Delete Workspace
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
                <label htmlFor="ws-is-active" style={{ margin: 0, fontWeight: 600 }}>Active</label>
              </div>
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

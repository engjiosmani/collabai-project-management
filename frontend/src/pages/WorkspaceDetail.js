import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";

import {
  getOrganization,
  getOrganizationWorkspaces,
  getWorkspaceMembers,
  updateWorkspace,
} from "../api/organizations";
import { deleteProject, fetchProjectsPaginated } from "../api/projects";
import { getApiErrorMessage } from "../api/api";
import AppSidebar from "../components/AppSidebar";
import ProjectFormModal from "../components/ProjectFormModal";
import EmptyState from "../components/ui/EmptyState";
import LoadingSkeleton from "../components/ui/LoadingSkeleton";
import { AuthContext } from "../context/AuthContext";
import "./Dashboard.css";

const ROLE_LABELS = {
  org_admin: "Organization Admin",
  workspace_admin: "Workspace Admin",
  manager: "Manager",
  member: "Member",
};

export default function WorkspaceDetail() {
  const { orgId, wsId } = useParams();
  const { user, isAdminOfOrg, isManagerOrAdminOfOrg } = useContext(AuthContext);

  const [org, setOrg] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [projects, setProjects] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [tab, setTab] = useState("overview");
  const [saving, setSaving] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [editProject, setEditProject] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [projectRefreshKey, setProjectRefreshKey] = useState(0);
  const [settingsForm, setSettingsForm] = useState({ name: "", description: "", is_active: true });

  const clear = () => { setError(""); setSuccess(""); };

  const orgIdNum = Number(orgId);
  const isOrgAdmin = isAdminOfOrg(orgIdNum);
  const isManagerOrAbove = isManagerOrAdminOfOrg(orgIdNum);
  const isWsAdmin = members.some(
    (m) => String(m.user_id) === String(user?.id) && m.role === "workspace_admin"
  );
  const canManageWorkspace = isOrgAdmin || isWsAdmin;

  const visibleTabs = useMemo(() => {
    const tabs = [
      ["overview", "Overview"],
      ["projects", "Projects"],
      ["members", "Members"],
    ];
    if (canManageWorkspace) {
      tabs.push(["settings", "Settings"]);
    }
    return tabs;
  }, [canManageWorkspace]);

  useEffect(() => {
    if (!visibleTabs.some(([v]) => v === tab)) setTab("overview");
  }, [tab, visibleTabs]);

  const loadData = useCallback(async () => {
    setLoading(true);
    clear();
    try {
      const orgData = await getOrganization(orgId);
      setOrg(orgData);
      const wsList = await getOrganizationWorkspaces(orgId);
      const ws = wsList.find((w) => String(w.id) === String(wsId));
      if (!ws) {
        setError("Workspace not found.");
        setLoading(false);
        return;
      }
      setWorkspace(ws);
      setSettingsForm({ name: ws.name || "", description: ws.description || "", is_active: ws.is_active !== false });
      const [memberData, projectData] = await Promise.all([
        getWorkspaceMembers(orgId, wsId),
        fetchProjectsPaginated({ workspace: wsId, page_size: 50 }),
      ]);
      setMembers(memberData);
      const projectResults = Array.isArray(projectData) ? projectData : projectData.results ?? [];
      setProjects(projectResults);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load workspace."));
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, wsId, projectRefreshKey]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleProjectCreated = () => {
    setShowCreateProject(false);
    setProjectRefreshKey((k) => k + 1);
    setSuccess("Project created.");
  };

  const handleEditSaved = () => {
    setEditProject(null);
    setProjectRefreshKey((k) => k + 1);
    setSuccess("Project updated.");
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteProject(deleteTarget.id);
      setDeleteTarget(null);
      setProjectRefreshKey((k) => k + 1);
      setSuccess("Project deleted.");
    } catch (err) {
      setDeleteError(getApiErrorMessage(err, "Could not delete project."));
    } finally {
      setDeleting(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    if (!settingsForm.name.trim()) return;
    setSaving(true);
    clear();
    try {
      const updated = await updateWorkspace(orgId, wsId, settingsForm);
      setWorkspace((prev) => ({ ...prev, ...updated }));
      setSettingsForm({ name: updated.name, description: updated.description || "", is_active: updated.is_active !== false });
      setSuccess("Workspace updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update workspace."));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <LoadingSkeleton variant="card" count={2} lines={5} label="Loading workspace" />
        </main>
      </div>
    );
  }

  if (error && !workspace) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <EmptyState icon="!" title="Could not load workspace" description={error} />
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main">
        <div className="org-detail-top">
          <Link to={`/organizations/${orgId}`} className="org-detail-back">&larr; {org?.name || "Organization"}</Link>
        </div>

        <div className="org-detail-header">
          <div className="org-detail-header-main">
            <p className="org-detail-eyebrow">Workspace</p>
            <h1 className="org-detail-name">{workspace?.name}</h1>
            <p className="org-detail-description">{workspace?.description || "No description"}</p>
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
              <h3>Projects</h3>
              <p className="orgs-overview-stat">{workspace?.project_count ?? projects.length}</p>
              <p className="orgs-overview-hint">Projects in this workspace</p>
            </section>
            <section className="orgs-overview-card">
              <h3>Members</h3>
              <p className="orgs-overview-stat">{workspace?.member_count ?? members.length}</p>
              <p className="orgs-overview-hint">Team members in this workspace</p>
            </section>
            <section className="orgs-overview-card">
              <h3>Status</h3>
              <p className="orgs-overview-stat orgs-overview-stat--role">
                {workspace?.is_active !== false ? "Active" : "Inactive"}
              </p>
              <p className="orgs-overview-hint">Workspace availability</p>
            </section>
          </div>
        )}

        {tab === "projects" && (
          <section className="org-detail-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
              <h3 className="org-detail-section-title" style={{ margin: 0 }}>Projects ({projects.length})</h3>
              <button
                type="button"
                className="dashboard-button dashboard-button--primary"
                style={{ padding: "10px 16px", fontSize: "0.85rem" }}
                onClick={() => setShowCreateProject(true)}
              >
                + New project
              </button>
            </div>
            {projects.length === 0 ? (
              <div className="org-empty-state">
                <p className="org-empty-message">No projects in this workspace yet.</p>
                <p className="org-empty-hint" style={{ marginTop: "4px", color: "#64748b", fontSize: "14px" }}>
                  Create a project inside this workspace to get started.
                </p>
              </div>
            ) : (
              <div className="org-workspace-list">
                {projects.map((p) => (
                  <article key={p.id} className="org-workspace-item" style={{ padding: "14px 16px" }}>
                    <div className="org-workspace-row" style={{ alignItems: "flex-start" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                          <span className="org-workspace-name">{p.name}</span>
                          <span
                            className="projects-panel-badge"
                            style={{
                              fontSize: "11px",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: p.is_active === false ? "#fee2e2" : "#dcfce7",
                              color: p.is_active === false ? "#991b1b" : "#166534",
                            }}
                          >
                            {p.is_active === false ? "Inactive" : "Active"}
                          </span>
                        </div>
                        {p.description && (
                          <p style={{ margin: "6px 0 0", color: "#475569", fontSize: "13px", lineHeight: "1.4" }}>
                            {p.description.length > 120 ? `${p.description.slice(0, 120)}…` : p.description}
                          </p>
                        )}
                        <div style={{ display: "flex", gap: "16px", marginTop: "8px", fontSize: "12px", color: "#64748b" }}>
                          {p.due_date && <span>Due: {p.due_date}</span>}
                          {p.member_count !== undefined && (
                            <span>{p.member_count} {p.member_count === 1 ? "member" : "members"}</span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "6px", flexShrink: 0, marginLeft: "12px" }}>
                        <Link
                          to={`/projects?project=${p.id}`}
                          className="dashboard-button"
                          style={{ padding: "6px 12px", fontSize: "12px", background: "#f1f5f9", color: "#334155", boxShadow: "none", textDecoration: "none", whiteSpace: "nowrap" }}
                        >
                          Open tasks
                        </Link>
                        {isManagerOrAbove && (
                          <button
                            type="button"
                            className="dashboard-button"
                            style={{ padding: "6px 12px", fontSize: "12px", background: "#f1f5f9", color: "#334155", boxShadow: "none" }}
                            onClick={() => setEditProject(p)}
                          >
                            Edit
                          </button>
                        )}
                        {isOrgAdmin && (
                          <button
                            type="button"
                            className="dashboard-button dashboard-button--danger"
                            style={{ padding: "6px 12px", fontSize: "12px" }}
                            onClick={() => { setDeleteTarget(p); setDeleteError(""); }}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "members" && (
          <section className="org-detail-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 className="org-detail-section-title" style={{ margin: 0 }}>Members ({members.length})</h3>
              {canManageWorkspace && (
                <span className="dashboard-button dashboard-button--ghost" style={{ padding: "10px 16px", fontSize: "0.85rem", opacity: 0.6, cursor: "default" }}>
                  Manage in workspace settings
                </span>
              )}
            </div>
            {members.length === 0 ? (
              <p className="org-empty-message">No members yet.</p>
            ) : (
              <div className="org-member-list">
                {members.map((member) => (
                  <div key={member.id} className="org-member-item">
                    <div className="org-member-info">
                      <strong>{member.username || member.user_username || member.email || `User #${member.user_id}`}</strong>
                      <p className="org-member-email">{member.email || member.user_email || ""}</p>
                      <span className="org-member-role-badge">{ROLE_LABELS[member.role] || member.role}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "settings" && canManageWorkspace && (
          <section className="org-detail-section">
            <h3 className="org-detail-section-title">Workspace Settings</h3>
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
              <div className="org-settings-field" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <input
                  id="ws-settings-active"
                  type="checkbox"
                  checked={settingsForm.is_active}
                  onChange={(e) => setSettingsForm((p) => ({ ...p, is_active: e.target.checked }))}
                  style={{ width: "18px", height: "18px" }}
                />
                <label htmlFor="ws-settings-active" style={{ margin: 0, fontWeight: 600 }}>Active</label>
              </div>
              <button className="dashboard-button dashboard-button--primary" type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Workspace"}
              </button>
            </form>
          </section>
        )}

        <ProjectFormModal
          open={showCreateProject}
          project={null}
          onClose={() => setShowCreateProject(false)}
          onSaved={handleProjectCreated}
          context="workspace"
          preselectOrg={{ id: Number(orgId), name: org?.name || "" }}
          preselectWs={{ id: Number(wsId), name: workspace?.name || "" }}
        />

        <ProjectFormModal
          open={Boolean(editProject)}
          project={editProject}
          onClose={() => setEditProject(null)}
          onSaved={handleEditSaved}
        />

        {deleteTarget && (
          <div className="org-modal-overlay" onClick={() => { setDeleteTarget(null); setDeleteError(""); }}>
            <div className="org-modal" onClick={(e) => e.stopPropagation()}>
              <h2 style={{ color: "#dc2626" }}>Delete Project</h2>
              <p className="org-delete-warning">
                Are you sure you want to delete <strong>{deleteTarget.name}</strong>? This will also remove all associated tasks and cannot be undone.
              </p>
              {deleteError && (
                <div className="org-flash-message org-flash-message--error" style={{ marginBottom: "12px" }}>{deleteError}</div>
              )}
              <div className="org-modal-actions">
                <button
                  type="button"
                  className="dashboard-button dashboard-button--ghost"
                  onClick={() => { setDeleteTarget(null); setDeleteError(""); }}
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
      </main>
    </div>
  );
}

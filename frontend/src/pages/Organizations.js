import { useEffect, useState } from "react";
import AppSidebar from "../components/AppSidebar";
import RoleGate from "../components/RoleGate";
import {
  createOrganization,
  getOrganizations,
  updateOrganization,
  getOrganizationMembers,
  inviteOrganizationMember,
  updateOrganizationMember,
  removeOrganizationMember,
  getOrganizationInvites,
  removeOrganizationInvite,
  getOrganizationWorkspaces,
  createWorkspace,
  getWorkspaceMembers,
  addWorkspaceMember,
  updateWorkspaceMember,
  removeWorkspaceMember,
} from "../api/organizations";
import { getApiErrorMessage } from "../api/api";
import "./Dashboard.css";

const ORG_ROLES = [
  { value: "member", label: "Member" },
  { value: "org_admin", label: "Organization Admin" },
];

const WORKSPACE_ROLES = [
  { value: "member", label: "Member" },
  { value: "manager", label: "Manager" },
  { value: "workspace_admin", label: "Workspace Admin" },
];

export default function Organizations() {
  const [tab, setTab] = useState("settings");

  const [organizations, setOrganizations] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);

  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspace, setActiveWorkspace] = useState(null);
  const [workspaceMembers, setWorkspaceMembers] = useState([]);

  const [form, setForm] = useState({ name: "", description: "" });
  const [newOrg, setNewOrg] = useState({ name: "", description: "" });
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member" });
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceMemberForm, setWorkspaceMemberForm] = useState({
    user_id: "",
    role: "member",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [addingWorkspaceMember, setAddingWorkspaceMember] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const clearMessages = () => {
    setError("");
    setSuccess("");
  };

  const emitWorkspaceChange = (workspaceId) => {
    window.dispatchEvent(
      new CustomEvent("workspace:changed", {
        detail: { workspaceId },
      })
    );
  };

  const emitOrganizationChange = (organizationId) => {
    window.dispatchEvent(
      new CustomEvent("organization:changed", {
        detail: { organizationId },
      })
    );
  };

  const loadMembers = async (organizationId) => {
    const data = await getOrganizationMembers(organizationId);
    setMembers(data);
  };

  const loadInvites = async (organizationId) => {
    const data = await getOrganizationInvites(organizationId);
    setInvites(data);
  };

  const loadWorkspaces = async (organizationId) => {
    const data = await getOrganizationWorkspaces(organizationId);
    setWorkspaces(data);

    const selected = activeWorkspace
      ? data.find((ws) => ws.id === activeWorkspace.id) || data[0]
      : data[0];

    setActiveWorkspace(selected || null);

    if (selected) {
      localStorage.setItem("active_workspace_id", String(selected.id));
      emitWorkspaceChange(String(selected.id));
      const wsMembers = await getWorkspaceMembers(organizationId, selected.id);
      setWorkspaceMembers(wsMembers);
    } else {
      localStorage.removeItem("active_workspace_id");
      emitWorkspaceChange(null);
      setWorkspaceMembers([]);
    }
  };

  const loadOrganizationData = async (organizationId) => {
    if (!organizationId) return;

    await Promise.all([
      loadMembers(organizationId),
      loadInvites(organizationId),
      loadWorkspaces(organizationId),
    ]);
  };

  const loadOrganizations = async () => {
    setLoading(true);
    clearMessages();

    try {
      const data = await getOrganizations();
      setOrganizations(data);

      const selected = activeOrg
        ? data.find((org) => org.id === activeOrg.id) || data[0]
        : data[0];

      setActiveOrg(selected || null);
      emitOrganizationChange(selected?.id ? String(selected.id) : null);
      setForm({
        name: selected?.name || "",
        description: selected?.description || "",
      });

      if (selected) {
        await loadOrganizationData(selected.id);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load organizations."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrganizations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectOrganization = async (org) => {
    setActiveOrg(org);
    setForm({ name: org.name || "", description: org.description || "" });
    setActiveWorkspace(null);
    localStorage.removeItem("active_workspace_id");
    emitWorkspaceChange(null);
    setWorkspaceMembers([]);
    clearMessages();

    emitOrganizationChange(String(org.id));

    try {
      await loadOrganizationData(org.id);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load organization data."));
    }
  };

  const selectWorkspace = async (workspace) => {
    if (!activeOrg) return;

    setActiveWorkspace(workspace);
    localStorage.setItem("active_workspace_id", String(workspace.id));
    emitWorkspaceChange(String(workspace.id));
    clearMessages();

    try {
      const data = await getWorkspaceMembers(activeOrg.id, workspace.id);
      setWorkspaceMembers(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load workspace members."));
    }
  };

  const handleCreateOrganization = async (e) => {
    e.preventDefault();

    if (!newOrg.name.trim()) {
      setError("Organization name is required.");
      return;
    }

    setCreating(true);
    clearMessages();

    try {
      const created = await createOrganization({
        name: newOrg.name.trim(),
        description: newOrg.description.trim(),
      });

      setNewOrg({ name: "", description: "" });
      setSuccess("Organization created successfully.");

      const updatedList = await getOrganizations();
      setOrganizations(updatedList);
      await selectOrganization(created);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to create organization."));
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateOrganization = async (e) => {
    e.preventDefault();
    if (!activeOrg) return;

    setSaving(true);
    clearMessages();

    try {
      const updated = await updateOrganization(activeOrg.id, form);

      setActiveOrg(updated);
      setOrganizations((prev) =>
        prev.map((org) => (org.id === updated.id ? updated : org))
      );
      setSuccess("Organization updated successfully.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update organization."));
    } finally {
      setSaving(false);
    }
  };

  const handleInviteMember = async (e) => {
    e.preventDefault();
    if (!activeOrg) return;

    if (!inviteForm.email.trim()) {
      setError("Email is required.");
      return;
    }

    setInviting(true);
    clearMessages();

    try {
      await inviteOrganizationMember(activeOrg.id, {
        email: inviteForm.email.trim(),
        role: inviteForm.role,
      });

      setInviteForm({ email: "", role: "member" });
      await loadInvites(activeOrg.id);
      setSuccess("Invitation request created successfully.");
      setTab("requests");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to invite member."));
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveInvite = async (invite) => {
    if (!activeOrg) return;
    if (!window.confirm(`Remove invitation request for ${invite.email}?`)) return;

    clearMessages();

    try {
      await removeOrganizationInvite(activeOrg.id, invite.id);
      await loadInvites(activeOrg.id);
      setSuccess("Invitation request removed.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to remove invitation request."));
    }
  };

  const handleChangeMemberRole = async (member, role) => {
    if (!activeOrg) return;

    clearMessages();

    try {
      await updateOrganizationMember(activeOrg.id, member.user_id, { role });
      await loadMembers(activeOrg.id);
      setSuccess("Member role updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update member role."));
    }
  };

  const handleRemoveMember = async (member) => {
    if (!activeOrg) return;
    if (!window.confirm(`Remove ${member.email} from this organization?`)) return;

    clearMessages();

    try {
      await removeOrganizationMember(activeOrg.id, member.user_id);
      await loadMembers(activeOrg.id);
      await loadWorkspaces(activeOrg.id);
      setSuccess("Member removed.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to remove member."));
    }
  };

  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!activeOrg) return;

    if (!workspaceName.trim()) {
      setError("Workspace name is required.");
      return;
    }

    setCreatingWorkspace(true);
    clearMessages();

    try {
      const workspace = await createWorkspace(activeOrg.id, {
        name: workspaceName.trim(),
      });

      setWorkspaceName("");
      await loadWorkspaces(activeOrg.id);
      await selectWorkspace(workspace);
      setSuccess("Workspace created successfully.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to create workspace."));
    } finally {
      setCreatingWorkspace(false);
    }
  };

  const handleAddWorkspaceMember = async (e) => {
    e.preventDefault();
    if (!activeOrg || !activeWorkspace) return;

    if (!workspaceMemberForm.user_id) {
      setError("Choose an organization member first.");
      return;
    }

    setAddingWorkspaceMember(true);
    clearMessages();

    try {
      await addWorkspaceMember(activeOrg.id, activeWorkspace.id, {
        user_id: Number(workspaceMemberForm.user_id),
        role: workspaceMemberForm.role,
      });

      setWorkspaceMemberForm({ user_id: "", role: "member" });
      const data = await getWorkspaceMembers(activeOrg.id, activeWorkspace.id);
      setWorkspaceMembers(data);
      setSuccess("Member added to workspace.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to add workspace member."));
    } finally {
      setAddingWorkspaceMember(false);
    }
  };

  const handleChangeWorkspaceRole = async (member, role) => {
    if (!activeOrg || !activeWorkspace) return;

    clearMessages();

    try {
      await updateWorkspaceMember(activeOrg.id, activeWorkspace.id, member.user_id, {
        role,
      });

      const data = await getWorkspaceMembers(activeOrg.id, activeWorkspace.id);
      setWorkspaceMembers(data);
      setSuccess("Workspace role updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update workspace role."));
    }
  };

  const handleRemoveWorkspaceMember = async (member) => {
    if (!activeOrg || !activeWorkspace) return;
    if (!window.confirm(`Remove ${member.email} from this workspace?`)) return;

    clearMessages();

    try {
      await removeWorkspaceMember(activeOrg.id, activeWorkspace.id, member.user_id);
      const data = await getWorkspaceMembers(activeOrg.id, activeWorkspace.id);
      setWorkspaceMembers(data);
      setSuccess("Workspace member removed.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to remove workspace member."));
    }
  };

  return (
    <div className="dashboard-shell">
      <AppSidebar />

      <main className="dashboard-main">
        <header className="dashboard-header">
          <div>
            <h1>Organizations</h1>
            <p>Manage organizations, members, invitations, and workspaces.</p>
          </div>

          {activeOrg && (
            <div style={styles.activePill}>
              Active organization: <strong>{activeOrg.name}</strong>
            </div>
          )}
        </header>

        {error && <div style={styles.error}>{error}</div>}
        {success && <div style={styles.success}>{success}</div>}

        {loading ? (
          <section className="dashboard-card">
            <p>Loading organizations...</p>
          </section>
        ) : (
          <div style={styles.layout}>
            <aside style={styles.leftPanel}>
              <section className="dashboard-card">
                <h2 style={styles.cardTitle}>My Organizations</h2>

                {organizations.length === 0 ? (
                  <p style={styles.muted}>No organizations yet.</p>
                ) : (
                  <div style={styles.orgList}>
                    {organizations.map((org) => (
                      <button
                        key={org.id}
                        type="button"
                        onClick={() => selectOrganization(org)}
                        style={{
                          ...styles.orgButton,
                          ...(activeOrg?.id === org.id ? styles.orgButtonActive : {}),
                        }}
                      >
                        <strong>{org.name}</strong>
                        <span>{org.description || "No description"}</span>
                      </button>
                    ))}
                  </div>
                )}

                <form onSubmit={handleCreateOrganization} style={styles.formBlock}>
                  <h3 style={styles.smallTitle}>Create Organization</h3>

                  <input
                    style={styles.input}
                    placeholder="Organization name"
                    value={newOrg.name}
                    onChange={(e) =>
                      setNewOrg((prev) => ({ ...prev, name: e.target.value }))
                    }
                  />

                  <textarea
                    style={styles.textarea}
                    placeholder="Description"
                    value={newOrg.description}
                    onChange={(e) =>
                      setNewOrg((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />

                  <button
                    className="dashboard-button dashboard-button--primary"
                    type="submit"
                    disabled={creating}
                  >
                    {creating ? "Creating..." : "Create Organization"}
                  </button>
                </form>
              </section>
            </aside>

            <section style={styles.mainPanel}>
              <div style={styles.tabBar}>
                {[
                  ["settings", "Settings"],
                  ["members", "Members"],
                  ["requests", `Requests (${invites.length})`],
                  ["workspaces", "Workspaces"],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setTab(value)}
                    style={{
                      ...styles.tabButton,
                      ...(tab === value ? styles.tabButtonActive : {}),
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {!activeOrg ? (
                <section className="dashboard-card">
                  <p style={styles.muted}>Select or create an organization first.</p>
                </section>
              ) : (
                <>
                  {tab === "settings" && (
                    <section className="dashboard-card">
                      <h2 style={styles.cardTitle}>Organization Settings</h2>

                      <form onSubmit={handleUpdateOrganization}>
                        <label style={styles.label}>Name</label>
                        <input
                          style={styles.input}
                          value={form.name}
                          onChange={(e) =>
                            setForm((prev) => ({ ...prev, name: e.target.value }))
                          }
                        />

                        <label style={styles.label}>Description</label>
                        <textarea
                          style={styles.textarea}
                          value={form.description}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              description: e.target.value,
                            }))
                          }
                        />

                        <RoleGate requiredRole="org_admin">
                          <button
                            className="dashboard-button dashboard-button--primary"
                            type="submit"
                            disabled={saving}
                          >
                            {saving ? "Saving..." : "Save Organization"}
                          </button>
                        </RoleGate>
                      </form>
                    </section>
                  )}

                  {tab === "members" && (
                    <>
                      <RoleGate requiredRole="org_admin">
                        <section className="dashboard-card">
                          <h2 style={styles.cardTitle}>Invite Member</h2>

                          <form onSubmit={handleInviteMember} style={styles.inlineForm}>
                            <input
                              style={styles.input}
                              placeholder="member@example.com"
                              value={inviteForm.email}
                              onChange={(e) =>
                                setInviteForm((prev) => ({
                                  ...prev,
                                  email: e.target.value,
                                }))
                              }
                            />

                            <select
                              style={styles.select}
                              value={inviteForm.role}
                              onChange={(e) =>
                                setInviteForm((prev) => ({
                                  ...prev,
                                  role: e.target.value,
                                }))
                              }
                            >
                              {ORG_ROLES.map((role) => (
                                <option key={role.value} value={role.value}>
                                  {role.label}
                                </option>
                              ))}
                            </select>

                            <button
                              className="dashboard-button dashboard-button--primary"
                              type="submit"
                              disabled={inviting}
                            >
                              {inviting ? "Inviting..." : "Invite"}
                            </button>
                          </form>
                        </section>
                      </RoleGate>

                      <section className="dashboard-card">
                        <h2 style={styles.cardTitle}>Members</h2>

                        {members.length === 0 ? (
                          <p style={styles.muted}>No members yet.</p>
                        ) : (
                          <div style={styles.list}>
                            {members.map((member) => (
                              <div key={member.id} style={styles.row}>
                                <div>
                                  <strong>{member.username || member.email}</strong>
                                  <p style={styles.subText}>{member.email}</p>
                                  <p style={styles.subText}>
                                    Job role: {member.job_role_name || member.job_role || "Not assigned"}
                                  </p>
                                </div>

                                <RoleGate requiredRole="org_admin">
                                  <div style={styles.actions}>
                                    <select
                                      style={styles.select}
                                      value={member.role}
                                      onChange={(e) =>
                                        handleChangeMemberRole(member, e.target.value)
                                      }
                                    >
                                      {ORG_ROLES.map((role) => (
                                        <option key={role.value} value={role.value}>
                                          {role.label}
                                        </option>
                                      ))}
                                    </select>

                                    <button
                                      type="button"
                                      style={styles.dangerButton}
                                      onClick={() => handleRemoveMember(member)}
                                    >
                                      Remove
                                    </button>
                                  </div>
                                </RoleGate>
                              </div>
                            ))}
                          </div>
                        )}
                      </section>
                    </>
                  )}

                  {tab === "requests" && (
                    <section className="dashboard-card">
                      <h2 style={styles.cardTitle}>Pending Requests</h2>

                      {invites.length === 0 ? (
                        <p style={styles.muted}>No pending invitation requests.</p>
                      ) : (
                        <div style={styles.list}>
                          {invites.map((invite) => (
                            <div key={invite.id} style={styles.requestRow}>
                              <div>
                                <strong>{invite.email}</strong>
                                <p style={styles.subText}>
                                  Role: {invite.role} · Status: Pending
                                </p>
                                <p style={styles.subText}>
                                  Expires:{" "}
                                  {invite.expires_at
                                    ? new Date(invite.expires_at).toLocaleString()
                                    : "Not specified"}
                                </p>
                              </div>

                              <RoleGate requiredRole="org_admin">
                                <button
                                  type="button"
                                  style={styles.dangerButton}
                                  onClick={() => handleRemoveInvite(invite)}
                                >
                                  Remove Request
                                </button>
                              </RoleGate>
                            </div>
                          ))}
                        </div>
                      )}
                    </section>
                  )}

                  {tab === "workspaces" && (
                    <div style={styles.workspaceLayout}>
                      <section className="dashboard-card">
                        <h2 style={styles.cardTitle}>Workspaces</h2>

                        <RoleGate requiredRole="workspace_admin">
                          <form onSubmit={handleCreateWorkspace} style={styles.formBlockCompact}>
                            <input
                              style={styles.input}
                              placeholder="New workspace name"
                              value={workspaceName}
                              onChange={(e) => setWorkspaceName(e.target.value)}
                            />

                            <button
                              className="dashboard-button dashboard-button--primary"
                              type="submit"
                              disabled={creatingWorkspace}
                            >
                              {creatingWorkspace ? "Creating..." : "Create Workspace"}
                            </button>
                          </form>
                        </RoleGate>

                        <div style={styles.orgList}>
                          {workspaces.map((workspace) => (
                            <button
                              key={workspace.id}
                              type="button"
                              onClick={() => selectWorkspace(workspace)}
                              style={{
                                ...styles.orgButton,
                                ...(activeWorkspace?.id === workspace.id
                                  ? styles.orgButtonActive
                                  : {}),
                              }}
                            >
                              <strong>{workspace.name}</strong>
                              <span>
                                {workspace.member_count ?? 0} members ·{" "}
                                {workspace.is_active ? "Active" : "Inactive"}
                              </span>
                            </button>
                          ))}
                        </div>
                      </section>

                      <section className="dashboard-card">
                        <h2 style={styles.cardTitle}>Workspace Members</h2>

                        {!activeWorkspace ? (
                          <p style={styles.muted}>Select a workspace first.</p>
                        ) : (
                          <>
                            <RoleGate requiredRole="workspace_admin">
                              <form onSubmit={handleAddWorkspaceMember} style={styles.inlineForm}>
                                <select
                                  style={styles.select}
                                  value={workspaceMemberForm.user_id}
                                  onChange={(e) =>
                                    setWorkspaceMemberForm((prev) => ({
                                      ...prev,
                                      user_id: e.target.value,
                                    }))
                                  }
                                >
                                  <option value="">Choose org member</option>
                                  {members.map((member) => (
                                    <option key={member.user_id} value={member.user_id}>
                                      {member.email}
                                    </option>
                                  ))}
                                </select>

                                <select
                                  style={styles.select}
                                  value={workspaceMemberForm.role}
                                  onChange={(e) =>
                                    setWorkspaceMemberForm((prev) => ({
                                      ...prev,
                                      role: e.target.value,
                                    }))
                                  }
                                >
                                  {WORKSPACE_ROLES.map((role) => (
                                    <option key={role.value} value={role.value}>
                                      {role.label}
                                    </option>
                                  ))}
                                </select>

                                <button
                                  className="dashboard-button dashboard-button--primary"
                                  type="submit"
                                  disabled={addingWorkspaceMember}
                                >
                                  {addingWorkspaceMember ? "Adding..." : "Add Member"}
                                </button>
                              </form>
                            </RoleGate>

                            {workspaceMembers.length === 0 ? (
                              <p style={styles.muted}>No workspace members yet.</p>
                            ) : (
                              <div style={styles.list}>
                                {workspaceMembers.map((member) => (
                                  <div key={member.id} style={styles.row}>
                                    <div>
                                      <strong>{member.username || member.email}</strong>
                                      <p style={styles.subText}>{member.email}</p>
                                    </div>

                                    <RoleGate requiredRole="workspace_admin">
                                      <div style={styles.actions}>
                                        <select
                                          style={styles.select}
                                          value={member.role}
                                          onChange={(e) =>
                                            handleChangeWorkspaceRole(member, e.target.value)
                                          }
                                        >
                                          {WORKSPACE_ROLES.map((role) => (
                                            <option key={role.value} value={role.value}>
                                              {role.label}
                                            </option>
                                          ))}
                                        </select>

                                        <button
                                          type="button"
                                          style={styles.dangerButton}
                                          onClick={() => handleRemoveWorkspaceMember(member)}
                                        >
                                          Remove
                                        </button>
                                      </div>
                                    </RoleGate>
                                  </div>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </section>
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  layout: {
    display: "grid",
    gridTemplateColumns: "320px 1fr",
    gap: "24px",
    alignItems: "start",
  },

  leftPanel: {
    position: "sticky",
    top: "20px",
  },

  mainPanel: {
    display: "grid",
    gap: "20px",
  },

  activePill: {
  background: "#eef2ff",
  border: "1px solid #c7d2fe",
  color: "#3730a3",
  padding: "10px 16px",
  borderRadius: "14px",
  fontSize: "14px",
  marginTop: "10px",
  marginBottom: "22px",
},

  tabBar: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
    background: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: "16px",
    padding: "8px",
  },

  tabButton: {
    border: "none",
    borderRadius: "10px",
    padding: "10px 18px",
    background: "transparent",
    color: "#334155",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "14px",
  },

  tabButtonActive: {
    background: "#4f46e5",
    color: "#ffffff",
  },

  workspaceLayout: {
    display: "grid",
    gridTemplateColumns: "380px 1fr",
    gap: "20px",
    alignItems: "start",
  },

  cardTitle: {
    marginTop: 0,
    marginBottom: "14px",
    fontSize: "18px",
    fontWeight: 700,
  },

  smallTitle: {
    marginTop: 0,
    marginBottom: "12px",
    fontSize: "16px",
    fontWeight: 700,
  },

  orgList: {
    display: "grid",
    gap: "10px",
  },

  orgButton: {
    textAlign: "left",
    border: "1px solid #d9e2ef",
    background: "#ffffff",
    borderRadius: "14px",
    padding: "14px 16px",
    cursor: "pointer",
    display: "grid",
    gap: "4px",
    color: "#0f172a",
    transition: "all 0.2s ease",
  },

  orgButtonActive: {
    borderColor: "#4f46e5",
    background: "#eef2ff",
  },

  formBlock: {
    borderTop: "1px solid #e5e7eb",
    marginTop: "20px",
    paddingTop: "20px",
    display: "grid",
    gap: "12px",
  },

  formBlockCompact: {
    display: "grid",
    gap: "10px",
    marginBottom: "16px",
  },

  inlineForm: {
    display: "grid",
    gridTemplateColumns: "1fr 200px auto",
    gap: "10px",
    alignItems: "center",
    marginBottom: "16px",
  },

  label: {
    display: "block",
    fontWeight: 600,
    marginBottom: "8px",
    marginTop: "12px",
    fontSize: "14px",
  },

  input: {
    width: "100%",
    border: "1px solid #d9e2ef",
    borderRadius: "12px",
    padding: "12px 14px",
    fontSize: "14px",
    boxSizing: "border-box",
    background: "#ffffff",
  },

  textarea: {
    width: "100%",
    minHeight: "120px",
    border: "1px solid #d9e2ef",
    borderRadius: "12px",
    padding: "12px 14px",
    fontSize: "14px",
    boxSizing: "border-box",
    resize: "vertical",
    background: "#ffffff",
  },

  select: {
    border: "1px solid #d9e2ef",
    borderRadius: "12px",
    padding: "12px 14px",
    fontSize: "14px",
    background: "#ffffff",
    minWidth: "160px",
  },

  list: {
    display: "grid",
    gap: "12px",
  },

  row: {
    display: "flex",
    justifyContent: "space-between",
    gap: "14px",
    alignItems: "center",
    border: "1px solid #e5e7eb",
    borderRadius: "14px",
    padding: "14px 16px",
    background: "#ffffff",
  },

  requestRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: "14px",
    alignItems: "center",
    border: "1px solid #fde68a",
    borderRadius: "14px",
    padding: "14px 16px",
    background: "#fffbeb",
  },

  subText: {
    margin: "4px 0 0",
    color: "#64748b",
    fontSize: "13px",
  },

  actions: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
  },

  dangerButton: {
    border: "none",
    borderRadius: "10px",
    padding: "10px 14px",
    background: "#dc2626",
    color: "#ffffff",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "14px",
  },

  muted: {
    color: "#64748b",
    fontSize: "14px",
  },

  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "12px 14px",
    borderRadius: "12px",
    marginBottom: "16px",
  },

  success: {
    background: "#dcfce7",
    color: "#166534",
    padding: "12px 14px",
    borderRadius: "12px",
    marginBottom: "16px",
  },
};
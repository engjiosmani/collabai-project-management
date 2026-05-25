import { useCallback, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  createOrganization,
  getOrganizations,
} from "../api/organizations";
import { getApiErrorMessage } from "../api/api";
import AppSidebar from "../components/AppSidebar";
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

export default function Organizations() {
  const navigate = useNavigate();
  const location = useLocation();
  const deletedOrgName = location.state?.deletedOrg || null;
  const [flashMessage] = useState(
    deletedOrgName ? `"${deletedOrgName}" has been deleted.` : ""
  );
  const { loadMemberships } = useContext(AuthContext);
  const { refreshOrganizations } = useOrganization();
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [creating, setCreating] = useState(false);

  const loadOrganizations = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getOrganizations();
      setOrganizations(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load organizations."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOrganizations();
    if (deletedOrgName) {
      window.history.replaceState({}, document.title);
    }
  }, [loadOrganizations, deletedOrgName]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const created = await createOrganization({
        name: form.name.trim(),
        description: form.description.trim(),
      });
      setModalOpen(false);
      setForm({ name: "", description: "" });
      await loadOrganizations();
      await refreshOrganizations?.();
      await loadMemberships?.();
      navigate(`/organizations/${created.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to create organization."));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main">
        <header className="dashboard-topbar">
          <div>
            <h1 className="dashboard-heading">Organizations</h1>
            <p className="dashboard-subheading">
              Companies or teams that contain workspaces, members, projects, and tasks.
            </p>
          </div>
          <div className="dashboard-meta">
            <button
              className="dashboard-button dashboard-button--primary"
              type="button"
              onClick={() => setModalOpen(true)}
            >
              Create organization
            </button>
          </div>
        </header>

        {flashMessage && (
          <div className="org-flash-message org-flash-message--success">{flashMessage}</div>
        )}
        {error && (
          <div className="org-flash-message org-flash-message--error">{error}</div>
        )}

        {loading ? (
          <LoadingSkeleton variant="card" count={3} lines={3} label="Loading organizations" />
        ) : organizations.length === 0 ? (
          <EmptyState
            icon="O"
            title="No organizations yet"
            description="Create an organization for your team, or accept an invitation from an existing one."
            actionLabel="Create organization"
            onAction={() => setModalOpen(true)}
          />
        ) : (
          <div className="orgs-grid">
            {organizations.map((org) => (
              <button
                key={org.id}
                type="button"
                className="org-card"
                onClick={() => navigate(`/organizations/${org.id}`)}
              >
                <div className="org-card-top">
                  <div className="org-card-icon">{org.name[0]?.toUpperCase() || "O"}</div>
                  {org.my_role && (
                    <span className="org-card-role-badge">{ROLE_LABELS[org.my_role] || org.my_role}</span>
                  )}
                </div>
                <div className="org-card-body">
                  <strong className="org-card-name">{org.name}</strong>
                  <p className="org-card-desc">{org.description || "No description"}</p>
                </div>
                <div className="org-card-footer">
                  <div className="org-card-meta">
                    <span className="org-card-meta-item">{org.member_count ?? 0} members</span>
                    {org.workspace_count !== undefined && org.workspace_count !== null && (
                      <span className="org-card-meta-item">{org.workspace_count} workspaces</span>
                    )}
                  </div>
                  <span className="org-card-open">Open &rarr;</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {modalOpen && (
        <div className="org-modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="org-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create organization</h2>
            <form onSubmit={handleCreate}>
              <div className="org-modal-field">
                <label>Organization name</label>
                <input
                  placeholder="e.g. Acme Corp"
                  value={form.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  autoFocus
                />
              </div>
              <div className="org-modal-field">
                <label>Description</label>
                <textarea
                  placeholder="Brief description of your organization"
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                />
              </div>
              <div className="org-modal-actions">
                <button
                  type="button"
                  className="dashboard-button dashboard-button--ghost"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="dashboard-button dashboard-button--primary"
                  disabled={creating || !form.name.trim()}
                >
                  {creating ? "Creating..." : "Create organization"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

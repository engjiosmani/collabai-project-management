import { useEffect, useState } from "react";
import AppSidebar from "../components/AppSidebar";
import EmptyState from "../components/ui/EmptyState";
import LoadingSkeleton from "../components/ui/LoadingSkeleton";
import { acceptInvite, getMyInvitations } from "../api/organizations";
import { getApiErrorMessage } from "../api/api";
import "./Dashboard.css";

const ROLE_LABELS = {
  org_admin: "Organization Admin",
  workspace_admin: "Workspace Admin",
  manager: "Manager",
  member: "Member",
};

export default function Invitations() {
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acceptingToken, setAcceptingToken] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadInvites = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getMyInvitations();
      setInvites(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load invitations."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvites();
  }, []);

  const handleAccept = async (invite) => {
    setAcceptingToken(invite.token);
    setError("");
    setSuccess("");

    try {
      await acceptInvite(invite.token);
      setSuccess("Invitation accepted successfully.");
      await loadInvites();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to accept invitation."));
    } finally {
      setAcceptingToken("");
    }
  };

  return (
    <div className="dashboard-shell">
      <AppSidebar />

      <main className="dashboard-main">
        <header className="dashboard-header">
          <div>
            <h1>Invitations</h1>
            <p>Accept invitations to organizations and workspaces.</p>
          </div>
        </header>

        {error && <div style={styles.error}>{error}</div>}
        {success && <div style={styles.success}>{success}</div>}

        {loading ? (
          <LoadingSkeleton variant="card" count={2} lines={3} label="Loading invitations" />
        ) : invites.length === 0 ? (
          <EmptyState
            icon="I"
            title="No pending invitations"
            description="When an admin invites you, the invitation will appear here."
            className="dashboard-card"
          />
        ) : (
          <div style={styles.grid}>
            {invites.map((invite) => (
              <section key={invite.id} className="dashboard-card">
                <div style={styles.inviteHeader}>
                  <div>
                    <h2 style={styles.cardTitle}>
                      {invite.organization_name || "Organization Invitation"}
                    </h2>
                    <p style={styles.muted}>{invite.email}</p>
                  </div>

                  <span style={styles.badge}>Pending</span>
                </div>

                <div style={styles.details}>
                  <p>
                    <strong>Role:</strong> {ROLE_LABELS[invite.role] || invite.role}
                  </p>

                  {invite.workspace_name ? (
                    <p>
                      <strong>Workspace:</strong> {invite.workspace_name}
                    </p>
                  ) : (
                    <p>
                      <strong>Scope:</strong> Organization
                    </p>
                  )}

                  <p>
                    <strong>Expires:</strong>{" "}
                    {invite.expires_at
                      ? new Date(invite.expires_at).toLocaleString()
                      : "Not specified"}
                  </p>
                </div>

                <button
                  className="dashboard-button dashboard-button--primary"
                  type="button"
                  disabled={acceptingToken === invite.token}
                  onClick={() => handleAccept(invite)}
                >
                  {acceptingToken === invite.token ? "Accepting" : "Accept Invitation"}
                </button>
              </section>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  grid: {
    display: "grid",
    gap: "14px",
    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  },
  inviteHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "flex-start",
    marginBottom: "16px",
  },
  cardTitle: {
    margin: 0,
  },
  badge: {
    background: "#fffbeb",
    color: "#92400e",
    border: "1px solid #fde68a",
    borderRadius: "999px",
    padding: "6px 10px",
    fontWeight: 700,
    fontSize: "12px",
  },
  details: {
    display: "grid",
    gap: "4px",
    marginBottom: "18px",
  },
  muted: {
    color: "#64748b",
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "12px 14px",
    borderRadius: "8px",
    marginBottom: "16px",
  },
  success: {
    background: "#dcfce7",
    color: "#166534",
    padding: "12px 14px",
    borderRadius: "8px",
    marginBottom: "16px",
  },
};

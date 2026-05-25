import { Link } from "react-router-dom";

import SettingsSection from "./SettingsSection";

const ROLE_LABELS = {
  org_admin: "Organization Admin",
  admin: "Organization Admin",
  workspace_admin: "Workspace Admin",
  manager: "Manager",
  member: "Member",
};

function RoleBadge({ role }) {
  const normalized = role || "member";
  const classRole = normalized === "admin" ? "org_admin" : normalized;

  return (
    <span className={`membership-role-badge membership-role-badge--${classRole}`}>
      {ROLE_LABELS[normalized] || normalized.replace(/_/g, " ")}
    </span>
  );
}

export default function MembershipsSection({ memberships }) {
  if (!memberships?.length) {
    return (
      <SettingsSection
        eyebrow="Access"
        title="Memberships"
        description="Organizations and workspaces currently connected to your account."
      >
        <div className="settings-empty-state">
          <p className="settings-empty-title">No memberships yet</p>
          <p className="settings-empty-text">
            You are not currently assigned to an organization or workspace.
          </p>
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      eyebrow="Access"
      title="Memberships"
      description="Organizations and workspaces currently connected to your account."
    >
      <div className="memberships-list">
        {memberships.map((membership) => {
          const org = membership.organization || {};
          const workspaces = membership.workspaces || [];
          const orgId = org.id;
          const orgName = org.name || "Unnamed organization";
          const initial = orgName[0]?.toUpperCase() || "O";

          return (
            <div className="membership-card" key={orgId || orgName}>
              <div className="membership-icon">{initial}</div>
              <div className="membership-body">
                <h3 className="membership-name">{orgName}</h3>
                <div className="membership-meta">
                  <RoleBadge role={membership.role} />
                  <span className="membership-count">
                    {workspaces.length} workspace{workspaces.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <div className="membership-action">
                <Link
                  to={orgId ? `/organizations/${orgId}` : "/organizations"}
                  className="dashboard-button dashboard-button--ghost"
                  style={{ padding: "8px 14px", fontSize: "0.82rem" }}
                >
                  Open
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </SettingsSection>
  );
}

import SettingsSection from "./SettingsSection";

const ROLE_LABELS = {
  org_admin: "Org admin",
  admin: "Org admin",
  workspace_admin: "Workspace admin",
  manager: "Manager",
  member: "Member",
};

function RoleBadge({ role }) {
  const normalized = role || "member";
  const classRole = normalized === "admin" ? "org_admin" : normalized;

  return (
    <span className={`settings-role-badge settings-role-badge--${classRole}`}>
      {ROLE_LABELS[normalized] || normalized.replace(/_/g, " ")}
    </span>
  );
}

export default function MembershipsSection({ memberships }) {
  return (
    <SettingsSection
      eyebrow="Access"
      title="Memberships"
      description="Organizations and workspaces currently connected to your account."
    >
      {!memberships?.length ? (
        <div className="settings-empty-state">
          <p className="settings-empty-title">No memberships yet</p>
          <p className="settings-empty-text">
            You are not currently assigned to an organization or workspace.
          </p>
        </div>
      ) : (
        <div className="memberships-list">
          {memberships.map((membership) => {
            const organization = membership.organization || {};
            const workspaces = membership.workspaces || [];

            return (
              <article
                className="membership-card"
                key={organization.id || organization.name}
              >
                <div className="membership-card-header">
                  <div>
                    <p className="membership-label">Organization</p>
                    <h3>{organization.name || "Unnamed organization"}</h3>
                  </div>
                  <RoleBadge role={membership.role} />
                </div>

                {workspaces.length ? (
                  <div className="workspace-list">
                    {workspaces.map((workspace) => (
                      <div className="workspace-row" key={workspace.id || workspace.name}>
                        <span>{workspace.name || "Unnamed workspace"}</span>
                        <RoleBadge role={workspace.role} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="settings-help-text">
                    No workspace memberships in this organization.
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </SettingsSection>
  );
}

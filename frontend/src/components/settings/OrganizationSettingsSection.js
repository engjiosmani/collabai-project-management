import { Link } from "react-router-dom";

import SettingsSection from "./SettingsSection";

export default function OrganizationSettingsSection() {
  return (
    <SettingsSection
      eyebrow="Admin"
      title="Organization Settings"
      description="Organization administration is available to users with org admin permission."
    >
      <div className="settings-empty-state">
        <p className="settings-empty-title">Manage organization details</p>
        <p className="settings-empty-text">
          Use the organization console for members, workspaces, invitations, and workspace settings.
        </p>
        <Link className="dashboard-button dashboard-button--primary settings-inline-link" to="/organizations">
          Open organizations
        </Link>
      </div>
    </SettingsSection>
  );
}

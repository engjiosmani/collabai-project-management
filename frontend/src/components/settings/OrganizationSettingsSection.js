import { Link } from "react-router-dom";

import SettingsSection from "./SettingsSection";

export default function OrganizationSettingsSection() {
  return (
    <SettingsSection
      eyebrow="Admin"
      title="Organization Settings"
      description="Organization administration is available to organization admins."
    >
      <div className="settings-empty-state">
        <p className="settings-empty-title">Manage organization details</p>
        <p className="settings-empty-text">
          Manage members, workspaces, invitations, and organization settings from the organization page.
        </p>
        <Link className="dashboard-button dashboard-button--primary settings-inline-link" to="/organizations">
          Open organizations
        </Link>
      </div>
    </SettingsSection>
  );
}

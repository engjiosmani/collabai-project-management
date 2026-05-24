import { useMemo, useState } from "react";

import AppSidebar from "../../components/AppSidebar";
import MembershipsSection from "../../components/settings/MembershipsSection";
import OrganizationSettingsSection from "../../components/settings/OrganizationSettingsSection";
import PasswordForm from "../../components/settings/PasswordForm";
import ProfileForm from "../../components/settings/ProfileForm";
import SettingsSidebar from "../../components/settings/SettingsSidebar";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton";
import useProfile from "../../hooks/useProfile";
import { useRole } from "../../hooks/useRole";
import "../Dashboard.css";
import "./Settings.css";

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("profile");
  const { isOrgAdmin } = useRole();
  const {
    profile,
    memberships,
    loading,
    error,
    reload,
    saveProfile,
    saveAvatar,
  } = useProfile();

  const content = useMemo(() => {
    if (activeSection === "password") {
      return <PasswordForm />;
    }

    if (activeSection === "memberships") {
      return <MembershipsSection memberships={memberships} />;
    }

    if (activeSection === "organization" && isOrgAdmin()) {
      return <OrganizationSettingsSection />;
    }

    return (
      <ProfileForm
        profile={profile}
        onSave={saveProfile}
        onAvatarUpload={saveAvatar}
      />
    );
  }, [activeSection, isOrgAdmin, memberships, profile, saveAvatar, saveProfile]);

  if (loading) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main settings-main">
          <div className="dashboard-topbar">
            <div>
              <div className="dashboard-skeleton-line dashboard-skeleton-line--title" />
              <div className="dashboard-skeleton-line" style={{ width: "360px" }} />
            </div>
          </div>
          <div className="settings-layout">
            <LoadingSkeleton variant="card" count={1} lines={4} label="Loading profile navigation" />
            <LoadingSkeleton variant="card" count={1} lines={8} label="Loading profile settings" />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main settings-main">
          <EmptyState
            icon="!"
            kicker="Settings"
            title="Settings could not load"
            description="Refresh the page or try again in a moment."
            actionLabel="Retry"
            onAction={reload}
            className="dashboard-empty-state dashboard-empty-state--error"
          />
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main settings-main">
        <div className="dashboard-topbar settings-topbar">
          <div>
            <h1 className="dashboard-heading">Settings</h1>
            <p className="dashboard-subheading">
              Manage your account profile, security, and workspace access.
            </p>
          </div>
        </div>

        <div className="settings-layout">
          <SettingsSidebar activeSection={activeSection} onSelect={setActiveSection} />
          <div className="settings-content">{content}</div>
        </div>
      </main>
    </div>
  );
}

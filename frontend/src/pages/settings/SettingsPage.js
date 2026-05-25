import { useContext, useMemo, useState } from "react";

import AppSidebar from "../../components/AppSidebar";
import MembershipsSection from "../../components/settings/MembershipsSection";
import PasswordForm from "../../components/settings/PasswordForm";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton";
import { AuthContext } from "../../context/AuthContext";
import useProfile from "../../hooks/useProfile";
import "../Dashboard.css";
import "./Settings.css";

const TABS = [
  { id: "security", label: "Security" },
  { id: "memberships", label: "Memberships" },
  { id: "preferences", label: "Preferences" },
];

export default function SettingsPage() {
  const { user } = useContext(AuthContext);
  const [activeSection, setActiveSection] = useState("security");
  const { memberships, loading, error, reload } = useProfile();

  const securityInfo = useMemo(() => {
    const items = [
      {
        label: "Email address",
        value: user?.email || "—",
      },
      {
        label: "Account status",
        value: (
          <span className="settings-security-badge settings-security-badge--active">
            <span className="settings-security-dot settings-security-dot--green" />
            Active
          </span>
        ),
      },
      {
        label: "Last login",
        value: user?.last_login
          ? new Date(user.last_login).toLocaleString()
          : "—",
      },
      {
        label: "Member since",
        value: user?.date_joined
          ? new Date(user.date_joined).toLocaleDateString(undefined, {
              year: "numeric",
              month: "long",
              day: "numeric",
            })
          : "—",
      },
      {
        label: "Two-factor authentication",
        value: (
          <span className="settings-security-badge settings-security-badge--disabled">
            Not enabled
          </span>
        ),
      },
    ];
    return items;
  }, [user]);

  const content = useMemo(() => {
    if (activeSection === "security") {
      return (
        <>
          <PasswordForm />
          <section className="settings-card">
            <div className="settings-card-header">
              <p className="settings-eyebrow">Status</p>
              <h2>Security summary</h2>
              <p>Current security status of your account.</p>
            </div>
            <div className="settings-security-grid">
              {securityInfo.map((item, i) => (
                <div key={i} className="settings-security-row">
                  <span className="settings-security-label">{item.label}</span>
                  <span className="settings-security-value">{item.value}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      );
    }

    if (activeSection === "memberships") {
      return <MembershipsSection memberships={memberships} />;
    }

    if (activeSection === "preferences") {
      return (
        <section className="settings-card">
          <div className="settings-card-header">
            <p className="settings-eyebrow">Preferences</p>
            <h2>Account Preferences</h2>
            <p>Customize your CollabAI experience.</p>
          </div>
          <div className="settings-prefs-grid">
            <div className="settings-prefs-row">
              <div>
                <div className="settings-prefs-label">Theme</div>
                <p className="settings-prefs-desc">Choose your preferred appearance</p>
              </div>
              <div className="settings-prefs-control">
                <span className="settings-prefs-coming-soon">Coming soon</span>
              </div>
            </div>
            <div className="settings-prefs-row">
              <div>
                <div className="settings-prefs-label">Notifications</div>
                <p className="settings-prefs-desc">Control email and in-app notifications</p>
              </div>
              <div className="settings-prefs-control">
                <span className="settings-prefs-coming-soon">Coming soon</span>
              </div>
            </div>
            <div className="settings-prefs-row">
              <div>
                <div className="settings-prefs-label">Timezone</div>
                <p className="settings-prefs-desc">Set your local timezone</p>
              </div>
              <div className="settings-prefs-control">
                <span className="settings-prefs-coming-soon">Coming soon</span>
              </div>
            </div>
            <div className="settings-prefs-row">
              <div>
                <div className="settings-prefs-label">Language</div>
                <p className="settings-prefs-desc">Interface language</p>
              </div>
              <div className="settings-prefs-control">
                <span className="settings-prefs-coming-soon">Coming soon</span>
              </div>
            </div>
          </div>
        </section>
      );
    }

    return null;
  }, [activeSection, memberships, securityInfo]);

  if (loading) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <div className="settings-container">
            <div className="settings-header">
              <div className="dashboard-skeleton-line dashboard-skeleton-line--title" />
              <div className="dashboard-skeleton-line" style={{ width: "360px" }} />
            </div>
            <LoadingSkeleton variant="card" count={1} lines={6} label="Loading settings" />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <div className="settings-container">
            <EmptyState
              icon="!"
              kicker="Settings"
              title="Settings could not load"
              description="Refresh the page or try again in a moment."
              actionLabel="Retry"
              onAction={reload}
              className="dashboard-empty-state dashboard-empty-state--error"
            />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main">
        <div className="settings-container">
          <header className="settings-header">
            <h1>Settings</h1>
            <p>Manage your account, security, and preferences.</p>
          </header>

          <div className="settings-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`settings-tab${activeSection === tab.id ? " settings-tab--active" : ""}`}
                onClick={() => setActiveSection(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="settings-content">{content}</div>
        </div>
      </main>
    </div>
  );
}

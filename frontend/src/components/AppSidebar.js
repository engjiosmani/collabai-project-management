import { useCallback, useContext, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { AuthContext } from "../context/AuthContext";

const STORAGE_KEY = "collabai-sidebar-collapsed";

function HamburgerIcon() {
  return (
    <span className="dashboard-sidebar-burger" aria-hidden>
      <span className="dashboard-sidebar-burger-line" />
      <span className="dashboard-sidebar-burger-line" />
      <span className="dashboard-sidebar-burger-line" />
    </span>
  );
}

/** @typedef {'tasks' | 'activity'} DashboardSection */

/**
 * Shared left nav (Dashboard look) + collapsible rail (hamburger only when collapsed).
 * @param {{ onNavigateSection?: (section: DashboardSection) => void }} props
 */
export default function AppSidebar({ onNavigateSection }) {
  const { logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [collapsed, setCollapsed] = useState(() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
    document.documentElement.dataset.sidebarCollapsed = collapsed ? "1" : "0";
    return () => {
      delete document.documentElement.dataset.sidebarCollapsed;
    };
  }, [collapsed]);

  const toggle = useCallback(() => {
    setCollapsed((c) => !c);
  }, []);

  const isDashboard = pathname === "/dashboard";
  const isProjects = pathname === "/projects";
  const isAI = pathname === "/ai";
  const isTeamPulse = pathname.startsWith("/ai/team-pulse");

  const navClass = (active) =>
    `dashboard-nav-item${active ? " dashboard-nav-item--active" : ""}`;

  const linkStyle = { textDecoration: "none", display: "block" };

  const renderSectionLink = (section, label, dataCy) => {
    const className = navClass(false);

    if (isDashboard && typeof onNavigateSection === "function") {
      return (
        <button
          className={className}
          data-cy={dataCy}
          type="button"
          onClick={() => onNavigateSection(section)}
        >
          {label}
        </button>
      );
    }

    return (
      <Link
        className={className}
        data-cy={dataCy}
        to="/dashboard"
        state={{ scrollTo: section }}
        style={linkStyle}
      >
        {label}
      </Link>
    );
  };

  return (
    <aside
      className={`dashboard-sidebar${collapsed ? " dashboard-sidebar--collapsed" : ""}`}
      aria-label="Main navigation"
    >
      <div className="dashboard-sidebar-inner">
        <div className="dashboard-sidebar-top">
          <button
            type="button"
            className="dashboard-sidebar-toggle"
            onClick={toggle}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand menu" : "Collapse menu"}
          >
            <HamburgerIcon />
          </button>

          {!collapsed ? (
            <>
              <div className="dashboard-brand">
                <div className="dashboard-brand-mark">C</div>
                <div>
                  <h1 className="dashboard-brand-title">CollabAI</h1>
                  <p className="dashboard-brand-subtitle">Project intelligence hub</p>
                </div>
              </div>

              <nav className="dashboard-nav dashboard-sidebar-nav" aria-label="App sections">
                <Link
                  className={navClass(isDashboard)}
                  data-cy="dashboard-nav-overview"
                  to="/dashboard"
                  style={linkStyle}
                >
                  Overview
                </Link>
                <Link
                  className={navClass(isProjects)}
                  data-cy="dashboard-nav-projects"
                  to="/projects"
                  style={linkStyle}
                >
                  Projects
                </Link>
                {renderSectionLink("tasks", "Tasks", "dashboard-nav-tasks")}
                {renderSectionLink("activity", "Activity", "dashboard-nav-activity")}
                <Link
                  className={navClass(isAI)}
                  data-cy="dashboard-nav-ai"
                  to="/ai"
                  style={linkStyle}
                >
                  AI Assistant
                </Link>
                <Link
                  className={navClass(isTeamPulse)}
                  to="/ai/team-pulse"
                  style={linkStyle}
                >
                  Team Pulse
                </Link>
              </nav>
            </>
          ) : null}
        </div>

        {!collapsed ? (
          <div className="dashboard-sidebar-footer">
            <p className="dashboard-sidebar-note" data-cy="dashboard-sidebar-note">
              Connected securely over REST using JWT authentication and the shared CollabAI API client.
            </p>
            <button
              className="dashboard-button dashboard-button--ghost"
              data-cy="dashboard-logout"
              type="button"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Logout
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

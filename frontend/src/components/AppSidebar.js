import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { AuthContext } from "../context/AuthContext";
import { useOrganization } from "../context/OrganizationContext";
import NotificationBell from "./notifications/NotificationBell";

const STORAGE_KEY = "collabai-sidebar-collapsed";

function UserChip() {
  const { user } = useContext(AuthContext);
  const menuRef = useRef(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  if (!user) return null;

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") ||
    user.username ||
    user.email ||
    "User";

  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const toggleMenu = () => setMenuOpen((v) => !v);
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="sidebar-user-dropdown-wrapper" ref={menuRef}>
      <button
        className="sidebar-user-chip"
        type="button"
        onClick={toggleMenu}
        aria-expanded={menuOpen}
        aria-label="Open user menu"
      >
        <div className="sidebar-user-avatar">
          {user.avatar ? (
            <img src={user.avatar} alt="" className="sidebar-user-avatar-img" />
          ) : (
            initials
          )}
        </div>
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{displayName}</span>
          <span className="sidebar-user-email">{user.email}</span>
        </div>
        <span className={`sidebar-user-chevron${menuOpen ? " sidebar-user-chevron--open" : ""}`} aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>

      {menuOpen && (
        <div className="sidebar-user-dropdown" role="menu">
          <Link
            className="sidebar-user-dropdown-item"
            to="/profile"
            role="menuitem"
            onClick={closeMenu}
          >
            View Profile
          </Link>
          <Link
            className="sidebar-user-dropdown-item"
            to="/settings"
            role="menuitem"
            onClick={closeMenu}
          >
            Account Settings
          </Link>
        </div>
      )}
    </div>
  );
}

function HamburgerIcon() {
  return (
    <span className="dashboard-sidebar-burger" aria-hidden>
      <span className="dashboard-sidebar-burger-line" />
      <span className="dashboard-sidebar-burger-line" />
      <span className="dashboard-sidebar-burger-line" />
    </span>
  );
}

function NavIcon({ type }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };

  const icons = {
    dashboard: (
      <svg {...common}>
        <path d="M3 13h8V3H3z" />
        <path d="M13 21h8V11h-8z" />
        <path d="M13 3h8v6h-8z" />
        <path d="M3 21h8v-6H3z" />
      </svg>
    ),
    organizations: (
      <svg {...common}>
        <path d="M3 21h18" />
        <path d="M5 21V7l7-4 7 4v14" />
        <path d="M9 21v-7h6v7" />
      </svg>
    ),
    projects: (
      <svg {...common}>
        <path d="M4 7h16" />
        <path d="M4 12h16" />
        <path d="M4 17h10" />
        <path d="M7 4v16" />
      </svg>
    ),
    tasks: (
      <svg {...common}>
        <path d="M9 11l2 2 4-5" />
        <path d="M5 4h14v16H5z" />
      </svg>
    ),
    invitations: (
      <svg {...common}>
        <path d="M4 6h16v12H4z" />
        <path d="m4 7 8 6 8-6" />
      </svg>
    ),
    ai: (
      <svg {...common}>
        <path d="M12 3v3" />
        <path d="M12 18v3" />
        <path d="M4.9 4.9 7 7" />
        <path d="m17 17 2.1 2.1" />
        <path d="M3 12h3" />
        <path d="M18 12h3" />
        <path d="M7 17l-2.1 2.1" />
        <path d="m19.1 4.9-2.1 2.1" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  };

  return <span className="dashboard-nav-icon">{icons[type]}</span>;
}

export default function AppSidebar({ onNavigateSection }) {
  const { logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const {
    organizations,
    activeOrganization,
    changeOrganization,
    loadingOrganizations,
  } = useOrganization();

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
    } catch {}

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
  const isTasks = pathname === "/tasks";
  const isOrganizations = pathname === "/organizations" || pathname.startsWith("/organizations/");
  const isInvitations = pathname === "/invitations";
  const isAI = pathname === "/ai";

  const hasNoOrg = organizations.length === 0;
  const navClass = (active, disabled) =>
    `dashboard-nav-item${active ? " dashboard-nav-item--active" : ""}${disabled ? " dashboard-nav-item--disabled" : ""}`;

  const linkStyle = { textDecoration: "none", display: "block" };

  const renderNavContent = (icon, label) => (
    <>
      <NavIcon type={icon} />
      <span className="dashboard-nav-label">{label}</span>
    </>
  );

  const renderSectionLink = (section, label, dataCy, disabled, icon) => {
    const isRoutingSection = section === "tasks";
    const className = navClass(isRoutingSection ? isTasks : false, disabled);

    if (disabled) {
      return (
        <span
          className={className}
          data-cy={dataCy}
          title="Create or join an organization first."
        >
          {renderNavContent(icon, label)}
        </span>
      );
    }

    if (!isRoutingSection && isDashboard && typeof onNavigateSection === "function") {
      return (
        <button
          className={className}
          data-cy={dataCy}
          type="button"
          onClick={() => onNavigateSection(section)}
        >
          {renderNavContent(icon, label)}
        </button>
      );
    }

    return (
      <Link
        className={className}
        data-cy={dataCy}
        to={isRoutingSection ? "/tasks" : "/dashboard"}
        state={isRoutingSection ? undefined : { scrollTo: section }}
        style={linkStyle}
      >
        {renderNavContent(icon, label)}
      </Link>
    );
  };

  const handleOrganizationChange = (event) => {
    const selected = organizations.find(
      (org) => String(org.id) === String(event.target.value)
    );

    if (selected) {
      changeOrganization(selected);
    }
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
          {collapsed ? (
            <div className="dashboard-sidebar-collapsed-bell">
              <NotificationBell />
            </div>
          ) : null}

          {!collapsed ? (
            <>
              <div className="dashboard-brand-row">
                <div className="dashboard-brand">
                  <div className="dashboard-brand-mark">C</div>
                  <div>
                    <h1 className="dashboard-brand-title">CollabAI</h1>
                    <p className="dashboard-brand-subtitle">Project management</p>
                  </div>
                </div>
                <NotificationBell />
              </div>

              <div style={styles.orgSwitcher}>
                <label style={styles.orgLabel}>Organization</label>

                <select
                  style={styles.orgSelect}
                  value={activeOrganization?.id || ""}
                  disabled={loadingOrganizations || organizations.length === 0}
                  onChange={handleOrganizationChange}
                >
                  {organizations.length === 0 ? (
                    <option value="">No organizations</option>
                  ) : (
                    organizations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <nav className="dashboard-nav dashboard-sidebar-nav" aria-label="App sections">
                <Link
                  className={navClass(isDashboard)}
                  data-cy="dashboard-nav-overview"
                  to="/dashboard"
                  style={linkStyle}
                >
                  {renderNavContent("dashboard", "Dashboard")}
                </Link>

                <Link
                  className={navClass(isOrganizations)}
                  to="/organizations"
                  style={linkStyle}
                >
                  {renderNavContent("organizations", "Organizations")}
                </Link>

                {hasNoOrg ? (
                  <span
                    className={navClass(isProjects, true)}
                    data-cy="dashboard-nav-projects"
                    title="Create or join an organization first."
                  >
                    {renderNavContent("projects", "Projects")}
                  </span>
                ) : (
                  <Link
                    className={navClass(isProjects)}
                    data-cy="dashboard-nav-projects"
                    to="/projects"
                    style={linkStyle}
                  >
                    {renderNavContent("projects", "Projects")}
                  </Link>
                )}

                {renderSectionLink("tasks", "Tasks", "dashboard-nav-tasks", hasNoOrg, "tasks")}

                <Link
                  className={navClass(isInvitations)}
                  to="/invitations"
                  style={linkStyle}
                >
                  {renderNavContent("invitations", "Invitations")}
                </Link>

                <Link
                  className={navClass(isAI)}
                  data-cy="dashboard-nav-ai"
                  to="/ai"
                  style={linkStyle}
                >
                  {renderNavContent("ai", "AI Assistant")}
                </Link>
              </nav>
            </>
          ) : null}
        </div>

        {!collapsed ? (
<div className="dashboard-sidebar-footer">
  <UserChip />
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

const styles = {
  orgSwitcher: {
    margin: "12px 0",
    padding: "8px",
    borderRadius: "8px",
    background: "rgba(255, 255, 255, 0.06)",
  },
  orgLabel: {
    display: "block",
    fontSize: "11px",
    color: "#94a3b8",
    marginBottom: "6px",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    fontWeight: 700,
  },
  orgSelect: {
    width: "100%",
    border: "1px solid rgba(148, 163, 184, 0.35)",
    borderRadius: "8px",
    padding: "8px 9px",
    background: "#111827",
    color: "#ffffff",
    fontSize: "13px",
    outline: "none",
  },
};

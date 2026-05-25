import RoleGate from "../RoleGate";

const ITEMS = [
  { id: "password", label: "Password" },
  { id: "memberships", label: "Memberships" },
  { id: "organization", label: "Organization", requiredRole: "org_admin" },
];

export default function SettingsSidebar({ activeSection, onSelect }) {
  return (
    <nav className="settings-sidebar" aria-label="Settings sections">
      {ITEMS.map((item) => {
        const button = (
          <button
            key={item.id}
            type="button"
            className={`settings-nav-item${
              activeSection === item.id ? " settings-nav-item--active" : ""
            }`}
            onClick={() => onSelect(item.id)}
          >
            {item.label}
          </button>
        );

        if (item.requiredRole) {
          return (
            <RoleGate key={item.id} requiredRole={item.requiredRole}>
              {button}
            </RoleGate>
          );
        }

        return button;
      })}
    </nav>
  );
}

export default function SettingsSection({ eyebrow, title, description, children }) {
  return (
    <section className="settings-card">
      <div className="settings-card-header">
        {eyebrow && <p className="settings-eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

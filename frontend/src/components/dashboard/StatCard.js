function StatCard({ label, value, hint, tone = "default" }) {
    return (
        <article className={`dashboard-stat-card dashboard-stat-card--${tone}`} data-cy={`stat-card-${label.toLowerCase().replace(/\s+/g, "-")}`}>
            <p className="dashboard-stat-label">{label}</p>
            <h3 className="dashboard-stat-value">{value}</h3>
            {hint ? <p className="dashboard-stat-hint">{hint}</p> : null}
        </article>
    );
}

export default StatCard;


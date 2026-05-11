function SkeletonCard({ lines = 3 }) {
    return (
        <div className="dashboard-skeleton-card" aria-hidden="true">
            <div className="dashboard-skeleton-line dashboard-skeleton-line--title" />
            {Array.from({ length: lines }).map((_, index) => (
                <div
                    className="dashboard-skeleton-line"
                    key={index}
                    style={{ width: `${85 - index * 12}%` }}
                />
            ))}
        </div>
    );
}

export default SkeletonCard;


function SkeletonLine({ width, className = "" }) {
    return (
        <span
            className={`ui-skeleton-line ${className}`.trim()}
            style={width ? { width } : undefined}
            aria-hidden="true"
        />
    );
}

function LoadingSkeleton({
    variant = "card",
    count = 1,
    lines = 3,
    className = "",
    label = "Loading content",
}) {
    return (
        <div className={className} role="status" aria-live="polite" aria-label={label}>
            <span className="ui-sr-only">{label}</span>
            {Array.from({ length: count }).map((_, index) => (
                <div
                    key={index}
                    className={`ui-skeleton ui-skeleton--${variant}`}
                    aria-hidden="true"
                >
                    <SkeletonLine className="ui-skeleton-line--title" />
                    {Array.from({ length: lines }).map((__, lineIndex) => (
                        <SkeletonLine
                            key={lineIndex}
                            width={`${Math.max(42, 88 - lineIndex * 14)}%`}
                        />
                    ))}
                </div>
            ))}
        </div>
    );
}

export { SkeletonLine };
export default LoadingSkeleton;

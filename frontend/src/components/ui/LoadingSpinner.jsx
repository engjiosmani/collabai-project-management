function LoadingSpinner({
    label = "Loading",
    size = "md",
    className = "",
    inline = false,
}) {
    const rootClass = inline ? "ui-spinner-inline" : "ui-spinner-state";

    return (
        <div
            className={`${rootClass} ${className}`.trim()}
            role="status"
            aria-live="polite"
            aria-label={label}
        >
            <span className={`ui-spinner ui-spinner--${size}`} aria-hidden="true" />
            <span className="ui-sr-only">{label}</span>
            {!inline ? <span className="ui-spinner-label">{label}</span> : null}
        </div>
    );
}

export default LoadingSpinner;

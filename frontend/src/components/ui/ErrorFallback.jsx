function ErrorFallback({
    title = "Something went wrong.",
    description = "Refresh the app or try again in a moment.",
    error,
    onReload,
    onRetry,
    className = "",
}) {
    const showDetails = process.env.NODE_ENV === "development" && error;

    return (
        <main className={`ui-error-page ${className}`.trim()} role="alert">
            <section className="ui-error-card">
                <div className="ui-error-icon" aria-hidden="true">
                    !
                </div>
                <p className="dashboard-empty-kicker">Application error</p>
                <h1>{title}</h1>
                <p>{description}</p>
                <div className="ui-error-actions">
                    {onRetry ? (
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--ghost"
                            onClick={onRetry}
                        >
                            Try again
                        </button>
                    ) : null}
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--primary"
                        onClick={onReload || (() => window.location.reload())}
                    >
                        Reload
                    </button>
                </div>
                {showDetails ? (
                    <details className="ui-error-details">
                        <summary>Error details</summary>
                        <pre>{error.stack || error.message || String(error)}</pre>
                    </details>
                ) : null}
            </section>
        </main>
    );
}

export default ErrorFallback;

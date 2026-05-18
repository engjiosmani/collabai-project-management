function ErrorState({ message, onRetry, onLogin, isAuthError }) {
    return (
        <section className="dashboard-empty-state dashboard-empty-state--error">
            <div>
                <p className="dashboard-empty-kicker">Dashboard unavailable</p>
                <h2>We couldn’t load the latest project data.</h2>
                <p className="dashboard-empty-text">{message}</p>
            </div>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                {onRetry ? (
                    <button className="dashboard-button dashboard-button--primary" onClick={onRetry} type="button">
                        Retry
                    </button>
                ) : null}
                {isAuthError && onLogin ? (
                    <button className="dashboard-button dashboard-button--ghost" onClick={onLogin} type="button">
                        Sign in again
                    </button>
                ) : null}
            </div>
        </section>
    );
}

export default ErrorState;

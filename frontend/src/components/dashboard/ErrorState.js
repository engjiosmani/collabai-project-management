function ErrorState({ message, onRetry }) {
    return (
        <section className="dashboard-empty-state dashboard-empty-state--error">
            <div>
                <p className="dashboard-empty-kicker">Dashboard unavailable</p>
                <h2>We couldn’t load the latest project data.</h2>
                <p className="dashboard-empty-text">{message}</p>
            </div>

            <button className="dashboard-button dashboard-button--primary" onClick={onRetry} type="button">
                Retry
            </button>
        </section>
    );
}

export default ErrorState;


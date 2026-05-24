/** Inline API error — same style as login form errors (red text only). */
function ErrorState({ message, onRetry }) {
    if (!message) {
        return null;
    }

    return (
        <div data-cy="dashboard-error" className="dashboard-inline-error">
            <p>{message}</p>
            {onRetry ? (
                <button type="button" onClick={onRetry}>
                    Retry
                </button>
            ) : null}
        </div>
    );
}

export default ErrorState;

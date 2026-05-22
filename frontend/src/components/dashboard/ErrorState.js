/** Inline API error — same style as login form errors (red text only). */
function ErrorState({ message }) {
    if (!message) {
        return null;
    }

    return (
        <p data-cy="dashboard-error" className="dashboard-inline-error">
            {message}
        </p>
    );
}

export default ErrorState;

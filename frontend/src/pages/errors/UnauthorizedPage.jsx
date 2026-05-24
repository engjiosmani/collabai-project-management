import { useNavigate } from "react-router-dom";

import "../Dashboard.css";

function UnauthorizedPage() {
    const navigate = useNavigate();

    return (
        <main className="ui-error-page">
            <section className="ui-error-card">
                <div className="ui-error-icon" aria-hidden="true">
                    !
                </div>
                <p className="dashboard-empty-kicker">Access restricted</p>
                <h1>You do not have permission to view this page.</h1>
                <p>
                    Contact your organization admin if you think your role should
                    include access.
                </p>
                <div className="ui-error-actions">
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--ghost"
                        onClick={() => navigate(-1)}
                    >
                        Go back
                    </button>
                    <button
                        type="button"
                        className="dashboard-button dashboard-button--primary"
                        onClick={() => navigate("/dashboard")}
                    >
                        Return to dashboard
                    </button>
                </div>
            </section>
        </main>
    );
}

export default UnauthorizedPage;

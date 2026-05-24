import { useContext } from "react";
import { useNavigate } from "react-router-dom";

import { AuthContext } from "../../context/AuthContext";
import "../Dashboard.css";

function NotFoundPage() {
    const navigate = useNavigate();
    const { accessToken } = useContext(AuthContext);
    const primaryTarget = accessToken ? "/dashboard" : "/login";

    return (
        <main className="ui-error-page">
            <section className="ui-error-card">
                <div className="ui-error-icon" aria-hidden="true">
                    404
                </div>
                <p className="dashboard-empty-kicker">Page not found</p>
                <h1>This page does not exist.</h1>
                <p>
                    The link may be outdated, or the page may have moved.
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
                        onClick={() => navigate(primaryTarget)}
                    >
                        {accessToken ? "Return to dashboard" : "Return to login"}
                    </button>
                </div>
            </section>
        </main>
    );
}

export default NotFoundPage;

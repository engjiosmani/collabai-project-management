import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

export default function Unauthorized() {
    const navigate = useNavigate();

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#f8fafc",
            }}
        >
            <div
                style={{
                    textAlign: "center",
                    maxWidth: "420px",
                    padding: "48px 32px",
                    background: "#ffffff",
                    borderRadius: "20px",
                    border: "1px solid #e5e7eb",
                    boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
                }}
            >
                <div
                    style={{
                        fontSize: "56px",
                        marginBottom: "16px",
                        lineHeight: 1,
                    }}
                >
                    🔒
                </div>
                <h1
                    style={{
                        fontSize: "24px",
                        fontWeight: 700,
                        color: "#0f172a",
                        margin: "0 0 10px",
                    }}
                >
                    Access Restricted
                </h1>
                <p
                    style={{
                        color: "#64748b",
                        fontSize: "15px",
                        lineHeight: 1.6,
                        margin: "0 0 28px",
                    }}
                >
                    You don't have permission to view this page. Contact your
                    organization admin if you think this is a mistake.
                </p>
                <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
                    <button
                        className="dashboard-button dashboard-button--primary"
                        onClick={() => navigate("/dashboard")}
                        type="button"
                    >
                        Go to Dashboard
                    </button>
                    <button
                        className="dashboard-button dashboard-button--ghost"
                        onClick={() => navigate(-1)}
                        type="button"
                    >
                        Go Back
                    </button>
                </div>
            </div>
        </div>
    );
}

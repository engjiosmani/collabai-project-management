import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import AppSidebar from "../components/AppSidebar";
import { acceptInvite } from "../api/organizations";
import { getApiErrorMessage } from "../api/api";
import "./Dashboard.css";

export default function AcceptInvite() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const isLoggedIn = Boolean(localStorage.getItem("access"));

  const handleAccept = async () => {
    setLoading(true);
    setMessage("");
    setError("");

    if (!isLoggedIn) {
      localStorage.setItem("pending_invite_token", token);
      navigate("/login");
      return;
    }

    try {
      await acceptInvite(token);
      setMessage("Invitation accepted successfully.");
      setTimeout(() => navigate("/dashboard"), 900);
    } catch (err) {
      setError(getApiErrorMessage(err, "Invitation is invalid or expired."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-shell">
      {isLoggedIn && <AppSidebar />}

      <main className="dashboard-main">
        <section className="dashboard-card" style={styles.card}>
          <h1 style={styles.title}>Accept Invitation</h1>
          <p style={styles.text}>
            You have been invited to join an organization in CollabAI.
          </p>

          {!isLoggedIn && (
            <div style={styles.info}>
              Please log in first. After login, return to Invitations or open this link again.
            </div>
          )}

          {message && <div style={styles.success}>{message}</div>}
          {error && <div style={styles.error}>{error}</div>}

          <button
            className="dashboard-button dashboard-button--primary"
            type="button"
            onClick={handleAccept}
            disabled={loading}
          >
            {loading ? "Accepting" : isLoggedIn ? "Accept Invite" : "Go to Login"}
          </button>
        </section>
      </main>
    </div>
  );
}

const styles = {
  card: {
    maxWidth: "720px",
    margin: "64px auto",
  },
  title: {
    marginTop: 0,
  },
  text: {
    color: "#64748b",
    marginBottom: "18px",
  },
  info: {
    background: "#eef2ff",
    color: "#3730a3",
    padding: "12px 14px",
    borderRadius: "12px",
    marginBottom: "16px",
  },
  success: {
    background: "#dcfce7",
    color: "#166534",
    padding: "12px 14px",
    borderRadius: "12px",
    marginBottom: "16px",
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "12px 14px",
    borderRadius: "12px",
    marginBottom: "16px",
  },
};

import { useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";

function Dashboard() {
    const { user, logout } = useContext(AuthContext);

    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    return (
        <div style={styles.container}>
            <div style={styles.sidebar}>
                <h2 style={styles.logo}>
                    CollabAI
                </h2>

                <div style={styles.menu}>
                    <p style={styles.menuItem}>
                        Dashboard
                    </p>

                    <p style={styles.menuItem}>
                        Projects
                    </p>

                    <p style={styles.menuItem}>
                        Tasks
                    </p>

                    <p style={styles.menuItem}>
                        Team
                    </p>
                </div>

                <button
                    onClick={handleLogout}
                    style={styles.logoutButton}
                >
                    Logout
                </button>
            </div>

            <div style={styles.main}>
                <div style={styles.header}>
                    <div>
                        <h1 style={styles.title}>
                            Welcome Back 
                        </h1>

                        <p style={styles.subtitle}>
                            Manage your projects with AI
                        </p>
                    </div>

                    <div style={styles.userCard}>
                        <p style={styles.userEmail}>
                            {user?.email}
                        </p>
                    </div>
                </div>

                <div style={styles.cards}>
                    <div style={styles.card}>
                        <h3 style={styles.cardTitle}>
                            Active Projects
                        </h3>

                        <p style={styles.cardValue}>
                            12
                        </p>
                    </div>

                    <div style={styles.card}>
                        <h3 style={styles.cardTitle}>
                            Pending Tasks
                        </h3>

                        <p style={styles.cardValue}>
                            28
                        </p>
                    </div>

                    <div style={styles.card}>
                        <h3 style={styles.cardTitle}>
                            Team Members
                        </h3>

                        <p style={styles.cardValue}>
                            8
                        </p>
                    </div>
                </div>

                <div style={styles.activityCard}>
                    <h2 style={styles.activityTitle}>
                        Recent Activity
                    </h2>

                    <p style={styles.activityText}>
                        No recent activities yet.
                    </p>
                </div>
            </div>
        </div>
    );
}

const styles = {
    container: {
        display: "flex",
        minHeight: "100vh",
        backgroundColor: "#f8fafc",
        fontFamily: "Arial",
    },

    sidebar: {
        width: "250px",
        backgroundColor: "#111827",
        color: "white",
        padding: "30px 20px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
    },

    logo: {
        fontSize: "28px",
        marginBottom: "40px",
    },

    menu: {
        display: "flex",
        flexDirection: "column",
        gap: "18px",
    },

    menuItem: {
        cursor: "pointer",
        fontSize: "16px",
        color: "#d1d5db",
    },

    logoutButton: {
        padding: "12px",
        borderRadius: "10px",
        border: "none",
        backgroundColor: "#ef4444",
        color: "white",
        cursor: "pointer",
        fontWeight: "bold",
    },

    main: {
        flex: 1,
        padding: "40px",
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "40px",
    },

    title: {
        fontSize: "34px",
        color: "#111827",
        marginBottom: "8px",
    },

    subtitle: {
        color: "#6b7280",
    },

    userCard: {
        backgroundColor: "white",
        padding: "15px 20px",
        borderRadius: "12px",
        boxShadow:
            "0 4px 20px rgba(0,0,0,0.06)",
    },

    userEmail: {
        margin: 0,
        color: "#374151",
        fontWeight: "bold",
    },

    cards: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "20px",
        marginBottom: "40px",
    },

    card: {
        backgroundColor: "white",
        padding: "25px",
        borderRadius: "16px",
        boxShadow:
            "0 4px 20px rgba(0,0,0,0.06)",
    },

    cardTitle: {
        color: "#6b7280",
        marginBottom: "15px",
    },

    cardValue: {
        fontSize: "34px",
        fontWeight: "bold",
        color: "#111827",
    },

    activityCard: {
        backgroundColor: "white",
        padding: "30px",
        borderRadius: "16px",
        boxShadow:
            "0 4px 20px rgba(0,0,0,0.06)",
    },

    activityTitle: {
        marginBottom: "15px",
        color: "#111827",
    },

    activityText: {
        color: "#6b7280",
    },
};

export default Dashboard;
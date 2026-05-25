import { useContext, useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";

function Login() {
    const { login } = useContext(AuthContext);

    const navigate = useNavigate();
    const location = useLocation();

    const [formData, setFormData] = useState({
        email: "",
        password: "",
    });

    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setError("");
        setSubmitting(true);

        try {
            const result = await login(
                formData.email,
                formData.password
            );

            if (result.success) {
                navigate("/dashboard");
            } else {
                setError(result.message || "Login failed. Please try again.");
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>
                    Welcome Back
                </h1>

                <p style={styles.subtitle}>
                    {location.state?.message || "Login to your CollabAI account"}
                </p>

                <form onSubmit={handleSubmit}>
                    <input
                        type="email"
                        name="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={handleChange}
                        data-cy="login-email"
                        style={styles.input}
                    />

                    <input
                        type="password"
                        name="password"
                        placeholder="Enter your password"
                        value={formData.password}
                        onChange={handleChange}
                        data-cy="login-password"
                        style={styles.input}
                    />

                    <div style={styles.forgotRow}>
                        <Link to="/forgot-password" style={styles.link}>
                            Forgot password?
                        </Link>
                    </div>

                    <button
                        type="submit"
                        data-cy="login-submit"
                        style={styles.button}
                        disabled={submitting}
                    >
                        {submitting ? "Logging in…" : "Login"}
                    </button>
                </form>

                {error && (
                    <p data-cy="login-error" style={styles.error}>
                        {error}
                    </p>
                )}

                <p style={styles.footerText}>
                    Don’t have an account?
                    <Link
                        to="/register"
                        style={styles.link}
                    >
                        {" "}
                        Register
                    </Link>
                </p>
            </div>
        </div>
    );
}

const styles = {
    container: {
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#f6f8fb",
        fontFamily: "Inter, Arial, sans-serif",
    },

    card: {
        width: "400px",
        backgroundColor: "white",
        padding: "32px",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
    },

    title: {
        fontSize: "26px",
        marginBottom: "10px",
        color: "#111827",
    },

    subtitle: {
        marginBottom: "30px",
        color: "#6b7280",
        fontSize: "15px",
    },

    input: {
        width: "100%",
        padding: "14px",
        marginBottom: "18px",
        borderRadius: "8px",
        border: "1px solid #d1d5db",
        fontSize: "15px",
        boxSizing: "border-box",
        outline: "none",
    },

    forgotRow: {
        marginTop: "-8px",
        marginBottom: "18px",
        textAlign: "right",
        fontSize: "14px",
    },

    button: {
        width: "100%",
        padding: "14px",
        backgroundColor: "#4f46e5",
        color: "white",
        border: "none",
        borderRadius: "8px",
        fontSize: "16px",
        fontWeight: "bold",
        cursor: "pointer",
        transition: "0.3s",
    },

    error: {
        marginTop: "15px",
        color: "red",
        fontSize: "14px",
    },

    footerText: {
        marginTop: "25px",
        textAlign: "center",
        color: "#6b7280",
    },

    link: {
        color: "#4f46e5",
        textDecoration: "none",
        fontWeight: "bold",
    },
};

export default Login;

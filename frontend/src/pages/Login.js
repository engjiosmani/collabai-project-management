import { useContext, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";

function Login() {
    const { login } = useContext(AuthContext);

    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        email: "",
        password: "",
    });

    const [error, setError] = useState("");

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setError("");

        const result = await login(
            formData.email,
            formData.password
        );

        if (result.success) {
            navigate("/dashboard");
        } else {
            setError(result.message);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>
                    Welcome Back
                </h1>

                <p style={styles.subtitle}>
                    Login to your CollabAI account
                </p>

                <form onSubmit={handleSubmit}>
                    <input
                        type="email"
                        name="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={handleChange}
                        style={styles.input}
                    />

                    <input
                        type="password"
                        name="password"
                        placeholder="Enter your password"
                        value={formData.password}
                        onChange={handleChange}
                        style={styles.input}
                    />

                    <button
                        type="submit"
                        style={styles.button}
                    >
                        Login
                    </button>
                </form>

                {error && (
                    <p style={styles.error}>
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
        background:
            "linear-gradient(to right, #eef2ff, #f8fafc)",
        fontFamily: "Arial",
    },

    card: {
        width: "400px",
        backgroundColor: "white",
        padding: "40px",
        borderRadius: "16px",
        boxShadow:
            "0 8px 30px rgba(0,0,0,0.08)",
    },

    title: {
        fontSize: "32px",
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
        borderRadius: "10px",
        border: "1px solid #d1d5db",
        fontSize: "15px",
        boxSizing: "border-box",
        outline: "none",
    },

    button: {
        width: "100%",
        padding: "14px",
        backgroundColor: "#4f46e5",
        color: "white",
        border: "none",
        borderRadius: "10px",
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
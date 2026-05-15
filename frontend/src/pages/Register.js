import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import API from "../api/api";

const extractApiErrorMessage = (data, fallback) => {
    if (!data) {
        return fallback;
    }

    if (typeof data === "string") {
        return data;
    }

    if (data.detail) {
        return data.detail;
    }

    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
        return data.non_field_errors[0];
    }

    const fieldMessages = Object.values(data)
        .flat()
        .filter(Boolean);

    return fieldMessages[0] || fallback;
};

function Register() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        email: "",
        password: "",
        confirmPassword: "",
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

        if (formData.password !== formData.confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        try {
            await API.post("/auth/register", {
                email: formData.email,
                password: formData.password,
            });

            navigate("/login");
        } catch (error) {
            setError(
                extractApiErrorMessage(
                    error.response?.data,
                    "Registration failed"
                )
            );
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>
                    Create Account
                </h1>

                <p style={styles.subtitle}>
                    Register to start using CollabAI
                </p>

                <p style={styles.passwordHint}>
                    Passwords must be at least 8 characters and should include uppercase, lowercase, a number, a special character, and avoid common passwords.
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

                    <input
                        type="password"
                        name="confirmPassword"
                        placeholder="Confirm password"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        style={styles.input}
                    />

                    <button
                        type="submit"
                        style={styles.button}
                    >
                        Register
                    </button>
                </form>

                {error && (
                    <p style={styles.error}>
                        {error}
                    </p>
                )}

                <p style={styles.footerText}>
                    Already have an account?
                    <Link
                        to="/login"
                        style={styles.link}
                    >
                        {" "}
                        Login
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

    passwordHint: {
        marginTop: "-18px",
        marginBottom: "18px",
        color: "#4b5563",
        fontSize: "13px",
        lineHeight: 1.5,
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

export default Register;
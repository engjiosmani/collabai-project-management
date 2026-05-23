import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../../api/api";
import { requestPasswordReset } from "../../services/authService";
import { emitToast } from "../../utils/formErrors";
import "./AuthPages.css";

const SUCCESS_MESSAGE = "If that email exists, a reset link has been sent.";

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [error, setErrorMessage] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { email: "" } });

  const onSubmit = async ({ email }) => {
    setErrorMessage("");
    setMessage("");

    try {
      await requestPasswordReset(email);
      setMessage(SUCCESS_MESSAGE);
      emitToast(SUCCESS_MESSAGE);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "Password reset request failed."));
    }
  };

  return (
    <div className="auth-page">
      <main className="auth-card" aria-labelledby="forgot-password-title">
        <h1 id="forgot-password-title">Reset your password</h1>
        <p className="auth-subtitle">Enter your email to request a password reset link.</p>

        <form className="auth-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="auth-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className={errors.email ? "auth-input auth-input--error" : "auth-input"}
              {...register("email", {
                required: "Email is required.",
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: "Enter a valid email address.",
                },
              })}
            />
            {errors.email && <p className="auth-error">{errors.email.message}</p>}
          </div>

          <button className="auth-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Sending..." : "Send reset link"}
          </button>
        </form>

        {message && <p className="auth-success">{message}</p>}
        {error && <p className="auth-error auth-error--block">{error}</p>}

        <p className="auth-footer">
          Remembered your password? <Link to="/login">Log in</Link>
        </p>
      </main>
    </div>
  );
}

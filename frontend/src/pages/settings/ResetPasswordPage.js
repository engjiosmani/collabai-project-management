import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../../api/api";
import { resetPassword } from "../../services/authService";
import { applyBackendFieldErrors, emitToast } from "../../utils/formErrors";
import { passwordRules } from "../../validation/passwordSchema";
import "./AuthPages.css";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";
  const [error, setErrorMessage] = useState("");
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      password: "",
      confirm_password: "",
    },
  });

  const password = watch("password");

  const onSubmit = async (values) => {
    setErrorMessage("");

    if (!token) {
      setErrorMessage("Invalid or expired token.");
      return;
    }

    try {
      await resetPassword({
        token,
        password: values.password,
        confirm_password: values.confirm_password,
      });
      emitToast("Password updated — please log in");
      navigate("/login", {
        replace: true,
        state: { message: "Password updated — please log in" },
      });
    } catch (error) {
      const applied = applyBackendFieldErrors(error, setError, {
        new_password: "password",
        password: "password",
      });
      if (!applied) {
        setErrorMessage(getApiErrorMessage(error, "Invalid or expired token."));
      }
    }
  };

  return (
    <div className="auth-page">
      <main className="auth-card" aria-labelledby="reset-password-title">
        <h1 id="reset-password-title">Choose a new password</h1>
        <p className="auth-subtitle">Create a new password for your CollabAI account.</p>

        {!token && <p className="auth-error auth-error--block">Invalid or expired token.</p>}

        <form className="auth-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="auth-field">
            <label htmlFor="password">New password</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              className={errors.password ? "auth-input auth-input--error" : "auth-input"}
              {...register("password", passwordRules)}
            />
            {errors.password && <p className="auth-error">{errors.password.message}</p>}
          </div>

          <div className="auth-field">
            <label htmlFor="confirm_password">Confirm password</label>
            <input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              className={
                errors.confirm_password ? "auth-input auth-input--error" : "auth-input"
              }
              {...register("confirm_password", {
                ...passwordRules,
                validate: (value) => value === password || "Passwords do not match.",
              })}
            />
            {errors.confirm_password && (
              <p className="auth-error">{errors.confirm_password.message}</p>
            )}
          </div>

          <button className="auth-button" type="submit" disabled={isSubmitting || !token}>
            {isSubmitting ? "Updating..." : "Update password"}
          </button>
        </form>

        {error && <p className="auth-error auth-error--block">{error}</p>}

        <p className="auth-footer">
          Back to <Link to="/login">log in</Link>
        </p>
      </main>
    </div>
  );
}

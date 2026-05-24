import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../../api/api";
import useChangePassword from "../../hooks/useChangePassword";
import { applyBackendFieldErrors, emitToast } from "../../utils/formErrors";
import { passwordRules } from "../../validation/passwordSchema";
import SettingsSection from "./SettingsSection";

const fieldClassName = (hasError) =>
  `settings-input${hasError ? " settings-input--error" : ""}`;

export default function PasswordForm() {
  const { saving, submit } = useChangePassword();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const newPassword = watch("new_password");
  const currentPassword = watch("current_password");

  const onSubmit = async (values) => {
    try {
      await submit(values);
      reset();
      emitToast("Password updated.");
    } catch (error) {
      const applied = applyBackendFieldErrors(error, setError, {
        old_password: "current_password",
      });
      if (!applied) {
        emitToast(getApiErrorMessage(error, "Password update failed."), "error");
      }
    }
  };

  const pending = saving || isSubmitting;

  return (
    <SettingsSection
      eyebrow="Security"
      title="Password"
      description="Change your password using your current credentials."
    >
      <form className="settings-form" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="settings-field">
          <label htmlFor="current_password">Current password</label>
          <input
            id="current_password"
            type="password"
            autoComplete="current-password"
            className={fieldClassName(errors.current_password)}
            {...register("current_password", {
              ...passwordRules,
              validate: (value) =>
                value !== newPassword || "Current password cannot match new password.",
            })}
          />
          {errors.current_password && (
            <p className="settings-field-error">{errors.current_password.message}</p>
          )}
        </div>

        <div className="settings-field-grid">
          <div className="settings-field">
            <label htmlFor="new_password">New password</label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              className={fieldClassName(errors.new_password)}
              {...register("new_password", {
                ...passwordRules,
                validate: (value) =>
                  value !== currentPassword || "New password cannot match current password.",
              })}
            />
            {errors.new_password && (
              <p className="settings-field-error">{errors.new_password.message}</p>
            )}
          </div>

          <div className="settings-field">
            <label htmlFor="confirm_password">Confirm password</label>
            <input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              className={fieldClassName(errors.confirm_password)}
              {...register("confirm_password", {
                ...passwordRules,
                validate: (value) => value === newPassword || "Passwords do not match.",
              })}
            />
            {errors.confirm_password && (
              <p className="settings-field-error">{errors.confirm_password.message}</p>
            )}
          </div>
        </div>

        <div className="settings-password-hints">
          <p className="settings-help-text">
            Password must be at least 8 characters and include a letter and a number.
          </p>
        </div>

        <div className="settings-actions">
          <button
            type="submit"
            className="dashboard-button dashboard-button--primary"
            disabled={pending}
          >
            {pending ? "Updating..." : "Update password"}
          </button>
        </div>
      </form>
    </SettingsSection>
  );
}

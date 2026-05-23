import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../../api/api";
import { useAuth } from "../../context/AuthContext";
import { applyBackendFieldErrors, emitToast } from "../../utils/formErrors";
import { profileValidation } from "../../validation/profileSchema";
import AvatarUpload from "./AvatarUpload";
import SettingsSection from "./SettingsSection";

const fieldClassName = (hasError) =>
  `settings-input${hasError ? " settings-input--error" : ""}`;

export default function ProfileForm({ profile, onSave, onAvatarUpload }) {
  const { refreshProfile } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({
    defaultValues: {
      first_name: "",
      last_name: "",
      bio: "",
      phone_number: "",
    },
  });

  useEffect(() => {
    if (!profile) return;
    reset({
      first_name: profile.first_name || "",
      last_name: profile.last_name || "",
      bio: profile.bio || "",
      phone_number: profile.phone_number || "",
    });
  }, [profile, reset]);

  const onSubmit = async (values) => {
    try {
      const updated = await onSave(values);
      reset({
        first_name: updated.first_name || "",
        last_name: updated.last_name || "",
        bio: updated.bio || "",
        phone_number: updated.phone_number || "",
      });
      await refreshProfile?.();
      emitToast("Profile updated.");
    } catch (error) {
      const applied = applyBackendFieldErrors(error, setError);
      if (!applied) {
        emitToast(getApiErrorMessage(error, "Profile update failed."), "error");
      }
    }
  };

  const handleAvatarUpload = async (file) => {
    const updated = await onAvatarUpload(file);
    await refreshProfile?.();
    emitToast("Avatar updated.");
    return updated;
  };

  return (
    <SettingsSection
      eyebrow="Account"
      title="Profile"
      description="Keep your public profile details current across CollabAI."
    >
      <AvatarUpload
        profile={profile}
        onUpload={handleAvatarUpload}
        disabled={isSubmitting}
      />

      <form className="settings-form" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="settings-field-grid">
          <div className="settings-field">
            <label htmlFor="first_name">First name</label>
            <input
              id="first_name"
              className={fieldClassName(errors.first_name)}
              {...register("first_name", profileValidation.first_name)}
            />
            {errors.first_name && (
              <p className="settings-field-error">{errors.first_name.message}</p>
            )}
          </div>

          <div className="settings-field">
            <label htmlFor="last_name">Last name</label>
            <input
              id="last_name"
              className={fieldClassName(errors.last_name)}
              {...register("last_name", profileValidation.last_name)}
            />
            {errors.last_name && (
              <p className="settings-field-error">{errors.last_name.message}</p>
            )}
          </div>
        </div>

        <div className="settings-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            className="settings-input settings-input--readonly"
            value={profile?.email || ""}
            readOnly
          />
        </div>

        <div className="settings-field">
          <label htmlFor="phone_number">Phone number</label>
          <input
            id="phone_number"
            className={fieldClassName(errors.phone_number)}
            {...register("phone_number", profileValidation.phone_number)}
          />
          {errors.phone_number && (
            <p className="settings-field-error">{errors.phone_number.message}</p>
          )}
        </div>

        <div className="settings-field">
          <label htmlFor="bio">Bio</label>
          <textarea
            id="bio"
            rows={5}
            className={fieldClassName(errors.bio)}
            {...register("bio", profileValidation.bio)}
          />
          {errors.bio && <p className="settings-field-error">{errors.bio.message}</p>}
        </div>

        <div className="settings-actions">
          <button
            type="submit"
            className="dashboard-button dashboard-button--primary"
            disabled={isSubmitting || !isDirty}
          >
            {isSubmitting ? "Saving..." : "Save profile"}
          </button>
        </div>
      </form>
    </SettingsSection>
  );
}

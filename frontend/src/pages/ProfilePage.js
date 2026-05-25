import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../api/api";
import AppSidebar from "../components/AppSidebar";
import AvatarUpload from "../components/settings/AvatarUpload";
import EmptyState from "../components/ui/EmptyState";
import LoadingSkeleton from "../components/ui/LoadingSkeleton";
import { useAuth } from "../context/AuthContext";
import useProfile from "../hooks/useProfile";
import { applyBackendFieldErrors, emitToast } from "../utils/formErrors";
import { profileValidation } from "../validation/profileSchema";
import "./Dashboard.css";
import "./Profile.css";

const fieldClassName = (hasError) =>
  `profile-input${hasError ? " profile-input--error" : ""}`;

export default function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const {
    profile,
    loading,
    error,
    reload,
    saveProfile,
    saveAvatar,
  } = useProfile();

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
      const updated = await saveProfile(values);
      reset({
        first_name: updated.first_name || "",
        last_name: updated.last_name || "",
        bio: updated.bio || "",
        phone_number: updated.phone_number || "",
      });
      emitToast("Profile updated.");
    } catch (err) {
      const applied = applyBackendFieldErrors(err, setError);
      if (!applied) {
        emitToast(getApiErrorMessage(err, "Profile update failed."), "error");
      }
    }
  };

  const handleAvatarUpload = async (file) => {
    await saveAvatar(file);
    await refreshProfile?.();
    emitToast("Avatar updated.");
  };

  const displayName =
    [profile?.first_name, profile?.last_name].filter(Boolean).join(" ") ||
    user?.username ||
    user?.email ||
    "User";

  if (loading) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <LoadingSkeleton variant="card" count={1} lines={10} label="Loading profile" />
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-shell">
        <AppSidebar />
        <main className="dashboard-main">
          <div className="profile-page">
            <div className="profile-card">
              <EmptyState
                icon="!"
                kicker="Profile"
                title="Profile could not load"
                description="Refresh the page or try again in a moment."
                actionLabel="Retry"
                onAction={reload}
                className="dashboard-empty-state dashboard-empty-state--error"
              />
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <AppSidebar />
      <main className="dashboard-main">
        <div className="profile-page">
          <div className="profile-header">
            <h1 className="dashboard-heading">Profile</h1>
            <p className="dashboard-subheading">
              Your personal profile across CollabAI.
            </p>
          </div>

          <div className="profile-card">
            <div className="profile-avatar-section">
              <AvatarUpload
                profile={profile}
                onUpload={handleAvatarUpload}
                disabled={isSubmitting}
              />
              <h2 className="profile-name">{displayName}</h2>
              <p className="profile-email">{profile?.email || user?.email}</p>
            </div>

            <form className="profile-form" onSubmit={handleSubmit(onSubmit)} noValidate>
              <div className="profile-field-grid">
                <div className="profile-field">
                  <label htmlFor="first_name">First name</label>
                  <input
                    id="first_name"
                    className={fieldClassName(errors.first_name)}
                    {...register("first_name", profileValidation.first_name)}
                  />
                  {errors.first_name && (
                    <p className="profile-field-error">{errors.first_name.message}</p>
                  )}
                </div>

                <div className="profile-field">
                  <label htmlFor="last_name">Last name</label>
                  <input
                    id="last_name"
                    className={fieldClassName(errors.last_name)}
                    {...register("last_name", profileValidation.last_name)}
                  />
                  {errors.last_name && (
                    <p className="profile-field-error">{errors.last_name.message}</p>
                  )}
                </div>
              </div>

              <div className="profile-field">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  className="profile-input profile-input--readonly"
                  value={profile?.email || ""}
                  readOnly
                />
              </div>

              <div className="profile-field">
                <label htmlFor="phone_number">Phone number</label>
                <input
                  id="phone_number"
                  type="tel"
                  placeholder="+383 44 123 456"
                  className={fieldClassName(errors.phone_number)}
                  {...register("phone_number", profileValidation.phone_number)}
                />
                {errors.phone_number ? (
                  <p className="profile-field-error">{errors.phone_number.message}</p>
                ) : null}
              </div>

              <div className="profile-field">
                <label htmlFor="bio">Bio</label>
                <textarea
                  id="bio"
                  rows={4}
                  className={fieldClassName(errors.bio)}
                  {...register("bio", profileValidation.bio)}
                />
                {errors.bio && <p className="profile-field-error">{errors.bio.message}</p>}
              </div>

              <div className="profile-actions">
                <button
                  type="submit"
                  className="dashboard-button dashboard-button--primary"
                  disabled={isSubmitting || !isDirty}
                >
                  {isSubmitting ? "Saving..." : "Save profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";

import { validateAvatarFile } from "../../validation/profileSchema";

const initialsFor = (profile) => {
  const name = [profile?.first_name, profile?.last_name].filter(Boolean).join(" ");
  const source = name || profile?.email || "User";
  return source
    .split(/[ @._-]+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
};

export default function AvatarUpload({ profile, onUpload, disabled }) {
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const avatarUrl = previewUrl || profile?.avatar || "";
  const initials = useMemo(() => initialsFor(profile), [profile]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    setError("");

    if (!file) return;

    const validationError = validateAvatarFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    const nextPreview = URL.createObjectURL(file);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(nextPreview);

    setUploading(true);
    try {
      await onUpload(file);
      setPreviewUrl("");
    } catch (err) {
      URL.revokeObjectURL(nextPreview);
      setPreviewUrl("");
      setError("Avatar upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="avatar-upload">
      <div className="avatar-upload-preview" aria-hidden>
        {avatarUrl ? (
          <img src={avatarUrl} alt="" />
        ) : (
          <span>{initials}</span>
        )}
      </div>

      <div className="avatar-upload-body">
        <label className="dashboard-button dashboard-button--ghost avatar-upload-button">
          <span>{uploading ? "Uploading" : "Upload avatar"}</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleFileChange}
            disabled={disabled || uploading}
          />
        </label>
        <p className="settings-help-text">JPG, PNG, GIF, or WebP. Maximum 2 MB.</p>
        {error && <p className="settings-field-error">{error}</p>}
      </div>
    </div>
  );
}

export const profileValidation = {
  first_name: {
    maxLength: {
      value: 150,
      message: "First name must be 150 characters or fewer.",
    },
  },
  last_name: {
    maxLength: {
      value: 150,
      message: "Last name must be 150 characters or fewer.",
    },
  },
  bio: {
    maxLength: {
      value: 1000,
      message: "Bio must be 1000 characters or fewer.",
    },
  },
  phone_number: {
    maxLength: {
      value: 40,
      message: "Phone number must be 40 characters or fewer.",
    },
    pattern: {
      value: /^[0-9+().\-\s]*$/,
      message: "Use a valid phone number.",
    },
  },
};

export const AVATAR_MAX_BYTES = 2 * 1024 * 1024;
export const AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

export const validateAvatarFile = (file) => {
  if (!file) return "";
  if (!AVATAR_ALLOWED_TYPES.includes(file.type)) {
    return "Upload a JPG, PNG, GIF, or WebP image.";
  }
  if (file.size > AVATAR_MAX_BYTES) {
    return "Avatar must be 2 MB or smaller.";
  }
  return "";
};

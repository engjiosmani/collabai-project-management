export const firstErrorMessage = (value) => {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return firstErrorMessage(value[0]);
  if (typeof value === "object") {
    const key = Object.keys(value)[0];
    return firstErrorMessage(value[key]);
  }
  return String(value);
};

export const applyBackendFieldErrors = (error, setError, fieldMap = {}) => {
  const data = error.response?.data;
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;

  let applied = false;
  Object.entries(data).forEach(([field, messages]) => {
    const mappedField = fieldMap[field] || field;
    if (!mappedField || mappedField === "detail" || mappedField === "non_field_errors") {
      return;
    }

    setError(mappedField, {
      type: "server",
      message: firstErrorMessage(messages) || "Invalid value.",
    });
    applied = true;
  });

  return applied;
};

export const emitToast = (message, tone = "success") => {
  if (typeof window === "undefined" || !message) return;
  window.dispatchEvent(
    new CustomEvent("app:toast", {
      detail: { message, tone },
    })
  );
};

const TYPE_CONFIG = {
  task: {
    label: "Task",
    icon: "T",
    tone: "info",
    path: "/tasks",
  },
  comment: {
    label: "Comment",
    icon: "C",
    tone: "success",
    path: "/tasks",
  },
  invitation: {
    label: "Invitation",
    icon: "I",
    tone: "warning",
    path: "/invitations",
  },
  organization: {
    label: "Organization",
    icon: "O",
    tone: "default",
    path: "/organizations",
  },
  project: {
    label: "Project",
    icon: "P",
    tone: "info",
    path: "/projects",
  },
  ai: {
    label: "AI",
    icon: "A",
    tone: "ai",
    path: "/ai",
  },
  system: {
    label: "System",
    icon: "S",
    tone: "default",
    path: null,
  },
};

const includesAny = (value, terms) =>
  terms.some((term) => value.includes(term));

export function getNotificationType(notification) {
  const haystack = `${notification?.title || ""} ${notification?.message || ""}`.toLowerCase();

  if (includesAny(haystack, ["invite", "invitation"])) return "invitation";
  if (includesAny(haystack, ["comment", "reply", "mention"])) return "comment";
  if (includesAny(haystack, ["task", "assigned", "assignment", "status"])) return "task";
  if (includesAny(haystack, ["project"])) return "project";
  if (includesAny(haystack, ["organization", "workspace"])) return "organization";
  if (includesAny(haystack, ["ai", "assistant"])) return "ai";

  return "system";
}

export function getNotificationConfig(notification) {
  const type = notification?.type || getNotificationType(notification);
  return TYPE_CONFIG[type] || TYPE_CONFIG.system;
}

export function getNotificationTarget(notification) {
  const explicitTarget =
    notification?.target_url ||
    notification?.url ||
    notification?.link ||
    notification?.metadata?.url ||
    notification?.metadata?.target_url;

  if (explicitTarget && String(explicitTarget).startsWith("/")) {
    return explicitTarget;
  }

  return getNotificationConfig(notification).path;
}

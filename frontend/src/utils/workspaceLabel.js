/**
 * Display label for a workspace in selects and project cards.
 * Shows workspace name only (no "Organization · Workspace" prefix).
 */
export function formatWorkspaceLabel(workspace) {
  if (!workspace) return "Your workspace";
  return workspace.name?.trim() || "My Workspace";
}

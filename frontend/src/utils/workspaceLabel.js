/**
 * Display label for a workspace in selects and greetings.
 * API returns { name, organization_name } from WorkspaceSerializer.
 */
export function formatWorkspaceLabel(workspace) {
  if (!workspace) return "Your workspace";
  const wsName = workspace.name?.trim() || "Workspace";
  const orgName = workspace.organization_name?.trim();
  if (!orgName || orgName === wsName) {
    return wsName;
  }
  return `${orgName} · ${wsName}`;
}

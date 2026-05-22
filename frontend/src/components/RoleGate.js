import { useRole } from "../hooks/useRole";

export default function RoleGate({ requiredRole, children }) {
    const { isOrgAdmin, isWorkspaceAdminOrAbove, isManagerOrAbove } = useRole();

    const roleChecks = {
        org_admin: isOrgAdmin,
        workspace_admin: isWorkspaceAdminOrAbove,
        manager: isManagerOrAbove,
    };

    const check = roleChecks[requiredRole];
    if (check && !check()) return null;

    return children;
}

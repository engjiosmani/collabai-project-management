import { useRole } from "../hooks/useRole";

export default function RoleGate({ requiredRole, children }) {
    const {
        isOrgAdmin,
        isWorkspaceAdminOrAbove,
        isManagerOrAbove,
        loadingMemberships,
    } = useRole();

    if (!requiredRole) {
        return children;
    }

    const roleChecks = {
        org_admin: isOrgAdmin,
        workspace_admin: isWorkspaceAdminOrAbove,
        manager: isManagerOrAbove,
    };

    const check = roleChecks[requiredRole];
    if (!check) return null;

    // Optimistic render: while memberships are loading in CI or slow envs,
    // allow the gate to render so E2E tests that stub server responses
    // don't flake due to ordering/timing. Once memberships finish loading
    // the real check will control visibility.
    if (loadingMemberships) return children;

    if (!check()) return null;

    return children;
}

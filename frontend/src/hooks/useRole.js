import { useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useOrganization } from "../context/OrganizationContext";

const normalizeRole = (role) => {
    if (!role) return null;
    return role === "admin" ? "org_admin" : role;
};

const roleRank = {
    member: 1,
    manager: 2,
    workspace_admin: 3,
    org_admin: 4,
};

export function useRole() {
    const auth = useContext(AuthContext);
    const organizationContext = useOrganization();
    const activeOrganization = organizationContext?.activeOrganization;
    const activeOrganizationId = activeOrganization?.id || localStorage.getItem("active_organization_id");
    const scopedRole = normalizeRole(
        activeOrganizationId ? auth?.orgRoles?.[activeOrganizationId] : auth?.role
    );
    const role = scopedRole || normalizeRole(auth?.role);
    const rank = roleRank[role] || 0;

    return {
        role,
        user: auth?.user || null,
        orgRole: role,
        workspaceRole: auth?.workspaceRole || null,
        loadingMemberships: !!auth?.loadingMemberships,
        isOrgAdmin: () => role === "org_admin",
        isWorkspaceAdminOrAbove: () => rank >= roleRank.workspace_admin,
        isManagerOrAbove: () => rank >= roleRank.manager,
    };
}

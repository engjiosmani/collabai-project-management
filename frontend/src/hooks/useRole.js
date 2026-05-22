import { useContext, useMemo } from "react";
import { AuthContext } from "../context/AuthContext";
import { useOrganization } from "../context/OrganizationContext";

const ROLE_WEIGHTS = {
    org_admin: 4,
    workspace_admin: 3,
    manager: 2,
    member: 1,
};

export function useRole() {
    const { memberships } = useContext(AuthContext);
    const { activeOrganization } = useOrganization();
    const activeWorkspaceId =
        typeof window !== "undefined" ? localStorage.getItem("active_workspace_id") : null;

    const membership = useMemo(() => {
        if (!memberships?.length || !activeOrganization) return null;
        return (
            memberships.find(
                (m) => String(m.organization.id) === String(activeOrganization.id)
            ) || null
        );
    }, [memberships, activeOrganization]);

    const orgRole = membership?.role || null;

    const activeWorkspaceMembership = useMemo(() => {
        if (!membership || !activeWorkspaceId) return null;

        return (
            (membership.workspaces || []).find(
                (workspace) => String(workspace.id) === String(activeWorkspaceId)
            ) || null
        );
    }, [activeWorkspaceId, membership]);

    const workspaceRole = activeWorkspaceMembership?.role || null;

    const workspaceRoles = useMemo(
        () => (membership?.workspaces || []).map((w) => w.role),
        [membership]
    );

    const effectiveWeight = useMemo(() => {
        const orgWeight = ROLE_WEIGHTS[orgRole] || 0;
        const workspaceWeight = ROLE_WEIGHTS[workspaceRole] || 0;
        return Math.max(orgWeight, workspaceWeight);
    }, [orgRole, workspaceRole]);

    const isOrgAdmin = () => orgRole === "org_admin";
    const isWorkspaceAdminOrAbove = () => effectiveWeight >= ROLE_WEIGHTS.workspace_admin;
    const isManagerOrAbove = () => effectiveWeight >= ROLE_WEIGHTS.manager;

    return {
        orgRole,
        workspaceRole,
        workspaceRoles,
        isOrgAdmin,
        isWorkspaceAdminOrAbove,
        isManagerOrAbove,
    };
}

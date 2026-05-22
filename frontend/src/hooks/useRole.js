import { useContext } from "react";
import { AuthContext } from "../context/AuthContext";

export function useRole() {
    const auth = useContext(AuthContext);

    return {
        role: auth?.role || null,
        user: auth?.user || null,
        orgRole: auth?.orgRole || null,
        workspaceRole: auth?.workspaceRole || null,
        loadingMemberships: !!auth?.loadingMemberships,
        isOrgAdmin: auth?.isOrgAdmin || (() => false),
        isWorkspaceAdminOrAbove: auth?.isWorkspaceAdminOrAbove || (() => false),
        isManagerOrAbove: auth?.isManagerOrAbove || (() => false),
    };
}

import { useContext } from "react";
import { Navigate } from "react-router-dom";

import FloatingAIAssistant from "../components/FloatingAIAssistant";
import { AuthContext } from "../context/AuthContext";
import { useRole } from "../hooks/useRole";

function ProtectedRoute({ children, requiredRole }) {
    const { accessToken } = useContext(AuthContext);
    const { isOrgAdmin, isWorkspaceAdminOrAbove, isManagerOrAbove } = useRole();

    if (!accessToken) {
        return <Navigate to="/login" />;
    }

    if (requiredRole) {
        const roleChecks = {
            org_admin: isOrgAdmin,
            workspace_admin: isWorkspaceAdminOrAbove,
            manager: isManagerOrAbove,
        };
        const check = roleChecks[requiredRole];
        if (check && !check()) {
            return <Navigate to="/unauthorized" />;
        }
    }

    return (
        <>
            {children}
            <FloatingAIAssistant />
        </>
    );
}

export default ProtectedRoute;
import { createContext, useEffect, useMemo, useState } from "react";
import API, { clearAuthStorage } from "../api/api";

const ROLE_WEIGHTS = {
    org_admin: 4,
    workspace_admin: 3,
    manager: 2,
    member: 1,
};

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [memberships, setMemberships] = useState([]);
    const [loadingMemberships, setLoadingMemberships] = useState(false);
    const [activeOrganizationId, setActiveOrganizationId] = useState(
        localStorage.getItem("active_organization_id") || null
    );
    const [activeWorkspaceId, setActiveWorkspaceId] = useState(
        localStorage.getItem("active_workspace_id") || null
    );

    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    useEffect(() => {
        const syncFromStorage = () => {
            const token = localStorage.getItem("access");
            const email = localStorage.getItem("user_email");
            const organizationId = localStorage.getItem("active_organization_id");
            const workspaceId = localStorage.getItem("active_workspace_id");

            setActiveOrganizationId(organizationId);
            setActiveWorkspaceId(workspaceId);

            if (token) {
                setAccessToken(token);
                setUser({
                    email: email || undefined,
                    authenticated: true,
                });
            } else {
                setAccessToken(null);
                setUser(null);
            }
        };

        syncFromStorage();

        const onTokenRefreshed = () => {
            const access = localStorage.getItem("access");
            if (access) {
                setAccessToken(access);
            }
        };

        const onLogout = () => {
            setAccessToken(null);
            setUser(null);
            setMemberships([]);
            setActiveOrganizationId(null);
            setActiveWorkspaceId(null);
        };

        const onOrganizationChanged = (event) => {
            setActiveOrganizationId(
                event.detail?.organizationId || localStorage.getItem("active_organization_id") || null
            );
        };

        const onWorkspaceChanged = (event) => {
            setActiveWorkspaceId(
                event.detail?.workspaceId || localStorage.getItem("active_workspace_id") || null
            );
        };

        window.addEventListener("auth:token-refreshed", onTokenRefreshed);
        window.addEventListener("auth:logout", onLogout);
        window.addEventListener("organization:changed", onOrganizationChanged);
        window.addEventListener("workspace:changed", onWorkspaceChanged);

        return () => {
            window.removeEventListener("auth:token-refreshed", onTokenRefreshed);
            window.removeEventListener("auth:logout", onLogout);
            window.removeEventListener("organization:changed", onOrganizationChanged);
            window.removeEventListener("workspace:changed", onWorkspaceChanged);
        };
    }, []);

    useEffect(() => {
        if (!accessToken) {
            setMemberships([]);
            setLoadingMemberships(false);
            return;
        }
        setLoadingMemberships(true);
        API.get("/profile/memberships/")
            .then((res) => {
                setMemberships(Array.isArray(res.data) ? res.data : res.data?.results || []);
            })
            .catch(() => {
                setMemberships([]);
            })
            .finally(() => {
                setLoadingMemberships(false);
            });
    }, [accessToken]);

    const activeMembership = useMemo(() => {
        if (!memberships.length) return null;

        const matchedById = activeOrganizationId
            ? memberships.find(
                  (membership) => String(membership.organization.id) === String(activeOrganizationId)
              )
            : null;

        return matchedById || memberships[0] || null;
    }, [activeOrganizationId, memberships]);

    const orgRole = activeMembership?.role || null;

    const workspaceRole = useMemo(() => {
        if (!activeMembership || !activeWorkspaceId) return null;

        return (
            activeMembership.workspaces?.find(
                (workspace) => String(workspace.id) === String(activeWorkspaceId)
            )?.role || null
        );
    }, [activeMembership, activeWorkspaceId]);

    const role = useMemo(() => {
        const orgWeight = ROLE_WEIGHTS[orgRole] || 0;
        const workspaceWeight = ROLE_WEIGHTS[workspaceRole] || 0;
        const effectiveWeight = Math.max(orgWeight, workspaceWeight);

        return (
            Object.entries(ROLE_WEIGHTS).find(([, weight]) => weight === effectiveWeight)?.[0] ||
            null
        );
    }, [orgRole, workspaceRole]);

    const isOrgAdmin = useMemo(() => () => role === "org_admin", [role]);

    const isWorkspaceAdminOrAbove = useMemo(
        () => () => (ROLE_WEIGHTS[role] || 0) >= ROLE_WEIGHTS.workspace_admin,
        [role]
    );

    const isManagerOrAbove = useMemo(
        () => () => (ROLE_WEIGHTS[role] || 0) >= ROLE_WEIGHTS.manager,
        [role]
    );

    const login = async (email, password) => {
        try {
            const response = await API.post("/auth/login", {
                email,
                password,
            });

            const access = response.data.access;
            const refresh = response.data.refresh;

            localStorage.setItem("access", access);
            localStorage.setItem("refresh", refresh);
            localStorage.setItem("user_email", email);

            setAccessToken(access);

            setUser({
                email,
                authenticated: true,
            });

            return {
                success: true,
            };
        } catch (error) {
            return {
                success: false,
                message: getApiErrorMessage(error, "Invalid credentials"),
            };
        }
    };

    const logout = () => {
        clearAuthStorage();
        setAccessToken(null);
        setUser(null);
        setMemberships([]);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                accessToken,
                memberships,
                loadingMemberships,
                role,
                orgRole,
                workspaceRole,
                activeOrganizationId,
                activeWorkspaceId,
                isOrgAdmin,
                isWorkspaceAdminOrAbove,
                isManagerOrAbove,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

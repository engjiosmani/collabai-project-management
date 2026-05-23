import { createContext, useCallback, useEffect, useState } from "react";
import API, { clearAuthStorage } from "../api/api";

export const AuthContext = createContext();

const normalizeRole = (role) => {
    if (!role) return null;
    if (role === "admin") return "org_admin";
    return role;
};

const getActiveOrganizationId = (orgs = [], memberships = []) => (
    localStorage.getItem("active_organization_id") ||
    orgs[0]?.id ||
    memberships[0]?.organization?.id ||
    null
);

const extractApiErrorMessage = (data, fallback) => {
    if (!data) return fallback;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0)
        return data.non_field_errors[0];
    return fallback;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    // user = { id, email, username, first_name, last_name, authenticated: true }

    const [orgRoles, setOrgRoles] = useState({});
    // { [orgId]: 'admin' | 'manager' | 'member' }

    const [role, setRole] = useState(null);
    const [orgRole, setOrgRole] = useState(null);
    const [workspaceRole, setWorkspaceRole] = useState(null);

    const [loadingMemberships, setLoadingMemberships] = useState(Boolean(localStorage.getItem("access")));

    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    const syncCurrentRole = useCallback((rolesMap, orgs = [], memberships = []) => {
        const activeOrganizationId = getActiveOrganizationId(orgs, memberships);
        if (!activeOrganizationId) {
            setRole(null);
            setOrgRole(null);
            setWorkspaceRole(null);
            return;
        }

        const rawRole = rolesMap[String(activeOrganizationId)] || null;
        const currentRole = normalizeRole(rawRole);

        setRole(currentRole);
        setOrgRole(currentRole && currentRole !== "workspace_admin" ? currentRole : null);
        setWorkspaceRole(currentRole === "workspace_admin" ? currentRole : null);
    }, []);

    // Fetch user profile + org roles after token is available
    const loadUserProfile = useCallback(async () => {
        setLoadingMemberships(true);

        try {
            const [meRes, orgsRes, membershipsRes] = await Promise.allSettled([
                API.get("/profile/"),
                API.get("/organizations/"),
                API.get("/profile/memberships/"),
            ]);

            if (meRes.status === "fulfilled") {
                const me = meRes.value.data;
                setUser({
                    id: me.id,
                    email: me.email || localStorage.getItem("user_email") || "",
                    username: me.username || "",
                    first_name: me.first_name || "",
                    last_name: me.last_name || "",
                    authenticated: true,
                });
            } else if (localStorage.getItem("user_email")) {
                setUser((current) =>
                    current || {
                        id: null,
                        email: localStorage.getItem("user_email") || "",
                        username: "",
                        first_name: "",
                        last_name: "",
                        authenticated: true,
                    }
                );
            }

            // Build orgId → role map
            const orgs = orgsRes.status === "fulfilled"
                ? (Array.isArray(orgsRes.value.data)
                    ? orgsRes.value.data
                    : orgsRes.value.data.results ?? [])
                : [];

            const memberships = membershipsRes.status === "fulfilled"
                ? (Array.isArray(membershipsRes.value.data)
                    ? membershipsRes.value.data
                    : membershipsRes.value.data.results ?? [])
                : [];

            const rolesMap = {};

            memberships.forEach((membership) => {
                const orgId = membership?.organization?.id ?? membership?.organization;
                if (orgId && membership?.role) {
                    rolesMap[String(orgId)] = membership.role;
                }
            });

            orgs.forEach((org) => {
                if (org.id && org.my_role) {
                    rolesMap[String(org.id)] = org.my_role;
                }
            });

            setOrgRoles(rolesMap);
            syncCurrentRole(rolesMap, orgs, memberships);
        } catch {
            // Profile load failure should not log the user out
        } finally {
            setLoadingMemberships(false);
        }
    }, [syncCurrentRole]);

    useEffect(() => {
        const token = localStorage.getItem("access");
        if (token) {
            setAccessToken(token);
            loadUserProfile();
        } else {
            setLoadingMemberships(false);
        }

        const onTokenRefreshed = (event) => {
            const access = event.detail?.access;
            if (access) setAccessToken(access);
        };
        const onLogout = () => {
            setAccessToken(null);
            setUser(null);
            setOrgRoles({});
            setRole(null);
            setOrgRole(null);
            setWorkspaceRole(null);
            setLoadingMemberships(false);
        };

        window.addEventListener("auth:token-refreshed", onTokenRefreshed);
        window.addEventListener("auth:logout", onLogout);
        return () => {
            window.removeEventListener("auth:token-refreshed", onTokenRefreshed);
            window.removeEventListener("auth:logout", onLogout);
        };
    }, [loadUserProfile]);

    useEffect(() => {
        const onOrganizationChanged = () => {
            syncCurrentRole(orgRoles);
        };

        window.addEventListener("organization:changed", onOrganizationChanged);
        return () => {
            window.removeEventListener("organization:changed", onOrganizationChanged);
        };
    }, [orgRoles, syncCurrentRole]);

    const login = async (email, password) => {
        try {
            const response = await API.post("/auth/login", { email, password });
            const { access, refresh } = response.data;

            localStorage.setItem("access", access);
            localStorage.setItem("refresh", refresh);
            localStorage.setItem("user_email", email);

            setAccessToken(access);
            // Load full profile (id, orgs, roles)
            await loadUserProfile();

            return { success: true };
        } catch (error) {
            return {
                success: false,
                message: extractApiErrorMessage(
                    error.response?.data,
                    "Invalid credentials"
                ),
            };
        }
    };

    const logout = () => {
        clearAuthStorage();
        setAccessToken(null);
        setUser(null);
        setOrgRoles({});
        setRole(null);
        setOrgRole(null);
        setWorkspaceRole(null);
        setLoadingMemberships(false);
    };

    // Helper: returns true if user is org_admin for that org
    const isAdminOfOrg = useCallback(
        (orgId) => ["admin", "org_admin", "workspace_admin"].includes(orgRoles[orgId]),
        [orgRoles]
    );

    // Helper: returns true if user is manager or admin for that org
    const isManagerOrAdminOfOrg = useCallback(
        (orgId) => ["admin", "org_admin", "workspace_admin", "manager"].includes(orgRoles[orgId]),
        [orgRoles]
    );

    const isOrgAdmin = useCallback(
        () => ["admin", "org_admin"].includes(role),
        [role]
    );

    const isWorkspaceAdminOrAbove = useCallback(
        () => ["admin", "org_admin", "workspace_admin"].includes(role),
        [role]
    );

    const isManagerOrAbove = useCallback(
        () => ["admin", "org_admin", "workspace_admin", "manager"].includes(role),
        [role]
    );

    return (
        <AuthContext.Provider
            value={{
                user,
                accessToken,
                role,
                orgRole,
                workspaceRole,
                orgRoles,
                loadingMemberships,
                isAdminOfOrg,
                isManagerOrAdminOfOrg,
                isOrgAdmin,
                isWorkspaceAdminOrAbove,
                isManagerOrAbove,
                login,
                logout,
                refreshProfile: loadUserProfile,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
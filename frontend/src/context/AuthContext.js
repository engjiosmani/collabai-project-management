import { createContext, useCallback, useContext, useEffect, useState } from "react";
import API, { clearAuthStorage } from "../api/api";

export const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

const normalizeRole = (role) => {
    if (!role) return null;
    if (role === "admin") return "org_admin";
    return role;
};

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
    const [orgRoles, setOrgRoles] = useState({});
    const [role, setRole] = useState(null);
    const [orgRole, setOrgRole] = useState(null);
    const [loadingMemberships, setLoadingMemberships] = useState(Boolean(localStorage.getItem("access")));
    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    const loadUserProfile = useCallback(async () => {
        setLoadingMemberships(true);
        try {
            const [meRes, orgsRes] = await Promise.all([
                API.get("/users/me/"),
                API.get("/organizations/"),
            ]);

            const me = meRes.data;
            setUser({
                id: me.id,
                email: me.email,
                username: me.username,
                first_name: me.first_name || "",
                last_name: me.last_name || "",
                avatar: me.profile?.avatar || null,
                authenticated: true,
            });

            const orgs = Array.isArray(orgsRes.data)
                ? orgsRes.data
                : orgsRes.data.results ?? [];

            const rolesMap = {};
            orgs.forEach((org) => {
                if (org.id && org.my_role) rolesMap[org.id] = org.my_role;
            });
            setOrgRoles(rolesMap);

            // Sync current role for the first org
            const firstOrgId = orgs[0]?.id;
            if (firstOrgId) {
                const rawRole = rolesMap[firstOrgId] || null;
                const currentRole = normalizeRole(rawRole);
                setRole(currentRole);
                setOrgRole(currentRole);
            }
        } catch {
            // Profile load failure must not log the user out
        } finally {
            setLoadingMemberships(false);
        }
    }, []);

    useEffect(() => {
        const token = localStorage.getItem("access");
        if (token) {
            setAccessToken(token);
            // Immediately hydrate user from localStorage so UI renders before API responds
            const storedEmail = localStorage.getItem("user_email");
            if (storedEmail) {
                setUser((prev) => prev || { email: storedEmail, authenticated: true });
            }
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
            setLoadingMemberships(false);
        };

        window.addEventListener("auth:token-refreshed", onTokenRefreshed);
        window.addEventListener("auth:logout", onLogout);
        return () => {
            window.removeEventListener("auth:token-refreshed", onTokenRefreshed);
            window.removeEventListener("auth:logout", onLogout);
        };
    }, [loadUserProfile]);

    const login = async (email, password) => {
        try {
            const response = await API.post("/auth/login", { email, password });
            const { access, refresh } = response.data;

            localStorage.setItem("access", access);
            localStorage.setItem("refresh", refresh);
            localStorage.setItem("user_email", email);

            setAccessToken(access);
            // Immediately set user from email so heading shows right away
            setUser((prev) => prev || { email, authenticated: true });
            await loadUserProfile();
            window.dispatchEvent(new Event("auth:login"));

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
        setLoadingMemberships(false);
    };

    const isAdminOfOrg = useCallback(
        (orgId) => orgRoles[orgId] === "admin" || orgRoles[orgId] === "org_admin",
        [orgRoles]
    );

    const isManagerOrAdminOfOrg = useCallback(
        (orgId) => ["admin", "org_admin", "manager"].includes(orgRoles[orgId]),
        [orgRoles]
    );

    const isOrgAdmin = useCallback(
        () => role === "org_admin" || role === "admin",
        [role]
    );

    const isManagerOrAbove = useCallback(
        () => ["org_admin", "admin", "manager"].includes(role),
        [role]
    );

    const isWorkspaceAdminOrAbove = useCallback(
        () => role === "workspace_admin" || role === "org_admin" || role === "admin",
        [role]
    );

    return (
        <AuthContext.Provider
            value={{
                user,
                accessToken,
                role,
                orgRole,
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
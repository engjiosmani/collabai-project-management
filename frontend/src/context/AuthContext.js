import { createContext, useCallback, useContext, useEffect, useState } from "react";
import API, { clearAuthStorage } from "../api/api";

export const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

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

    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    // Fetch user profile + org roles after token is available
    const loadUserProfile = useCallback(async () => {
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
                authenticated: true,
            });

            // Build orgId → role map
            const orgs = Array.isArray(orgsRes.data)
                ? orgsRes.data
                : orgsRes.data.results ?? [];
            const rolesMap = {};
            orgs.forEach((org) => {
                if (org.id && org.my_role) {
                    rolesMap[org.id] = org.my_role === "org_admin" ? "admin" : org.my_role;
                }
            });
            setOrgRoles(rolesMap);
        } catch {
            // Profile load failure should not log the user out
        }
    }, []);

    useEffect(() => {
        const token = localStorage.getItem("access");
        if (token) {
            setAccessToken(token);
            loadUserProfile();
        }

        const onTokenRefreshed = (event) => {
            const access = event.detail?.access;
            if (access) setAccessToken(access);
        };
        const onLogout = () => {
            setAccessToken(null);
            setUser(null);
            setOrgRoles({});
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
    };

    // Helper: returns true if user is org_admin for that org
    const isAdminOfOrg = useCallback(
        (orgId) => orgRoles[orgId] === "admin",
        [orgRoles]
    );

    // Helper: returns true if user is manager or admin for that org
    const isManagerOrAdminOfOrg = useCallback(
        (orgId) => ["admin", "manager"].includes(orgRoles[orgId]),
        [orgRoles]
    );

    return (
        <AuthContext.Provider
            value={{
                user,
                accessToken,
                orgRoles,
                isAdminOfOrg,
                isManagerOrAdminOfOrg,
                login,
                logout,
                refreshProfile: loadUserProfile,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
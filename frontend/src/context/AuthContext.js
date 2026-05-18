import { createContext, useEffect, useState } from "react";
import API, { clearAuthStorage } from "../api/api";

export const AuthContext = createContext();

const extractApiErrorMessage = (data, fallback) => {
    if (!data) {
        return fallback;
    }

    if (typeof data === "string") {
        return data;
    }

    if (data.detail) {
        return data.detail;
    }

    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
        return data.non_field_errors[0];
    }

    return fallback;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);

    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    useEffect(() => {
        const syncFromStorage = () => {
            const token = localStorage.getItem("access");
            const email = localStorage.getItem("user_email");

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

        const onTokenRefreshed = (event) => {
            const access = event.detail?.access;
            if (access) {
                setAccessToken(access);
            }
        };

        const onLogout = () => {
            setAccessToken(null);
            setUser(null);
        };

        window.addEventListener("auth:token-refreshed", onTokenRefreshed);
        window.addEventListener("auth:logout", onLogout);

        return () => {
            window.removeEventListener("auth:token-refreshed", onTokenRefreshed);
            window.removeEventListener("auth:logout", onLogout);
        };
    }, []);

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
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                accessToken,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
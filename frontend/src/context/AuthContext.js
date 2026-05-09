import { createContext, useEffect, useState } from "react";
import API from "../api/api";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);

    const [accessToken, setAccessToken] = useState(
        localStorage.getItem("access") || null
    );

    useEffect(() => {
        const token = localStorage.getItem("access");

        if (token) {
            setAccessToken(token);
            setUser({ authenticated: true });
        }
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
                message:
                    error.response?.data?.detail ||
                    "Invalid credentials",
            };
        }
    };

    const logout = () => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");

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
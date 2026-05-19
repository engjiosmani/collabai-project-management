import { useContext } from "react";
import { Navigate } from "react-router-dom";

import FloatingAIAssistant from "../components/FloatingAIAssistant";
import { AuthContext } from "../context/AuthContext";

function ProtectedRoute({ children }) {
    const { accessToken } = useContext(AuthContext);

    if (!accessToken) {
        return <Navigate to="/login" />;
    }

    return (
        <>
            {children}
            <FloatingAIAssistant />
        </>
    );
}

export default ProtectedRoute;
import { Routes, Route, Navigate } from "react-router-dom";

import Register from "./pages/Register";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AIAssistant from "./pages/AIAssistant";
import TeamPulse from "./pages/TeamPulse";
import Projects from "./pages/Projects";
import Organizations from "./pages/Organizations";
import Invitations from "./pages/Invitations";
import Unauthorized from "./pages/Unauthorized";
import ProtectedRoute from "./routes/ProtectedRoute";
import GlobalApiToast from "./components/GlobalApiToast";
import "./App.css";

function App() {
    return (
        <>
            <GlobalApiToast />
            <Routes>
                <Route
                    path="/"
                    element={<Navigate to="/login" />}
                />

                <Route
                    path="/register"
                    element={<Register />}
                />

                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/projects"
                    element={
                        <ProtectedRoute>
                            <Projects />
                        </ProtectedRoute>
                    }
                />

            <Route
                path="/ai"
                element={
                    <ProtectedRoute>
                        <AIAssistant />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/organizations"
                element={
                    <ProtectedRoute requiredRole="org_admin">
                        <Organizations />
                    </ProtectedRoute>
                }
            />

<Route
    path="/invitations"
    element={
                    <ProtectedRoute requiredRole="org_admin">
                        <Invitations />
                    </ProtectedRoute>
                }
            />

                <Route
                    path="/ai/team-pulse"
                    element={
                        <ProtectedRoute>
                            <TeamPulse />
                        </ProtectedRoute>
                    }
                />

                <Route path="/unauthorized" element={<Unauthorized />} />
            </Routes>
        </>
    );
}

export default App;

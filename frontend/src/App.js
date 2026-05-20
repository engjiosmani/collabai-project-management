import { Routes, Route, Navigate } from "react-router-dom";

import Register from "./pages/Register";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AIAssistant from "./pages/AIAssistant";
import TeamPulse from "./pages/TeamPulse";
import Projects from "./pages/Projects";

import ProtectedRoute from "./routes/ProtectedRoute";

function App() {
    return (
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
                path="/ai/team-pulse"
                element={
                    <ProtectedRoute>
                        <TeamPulse />
                    </ProtectedRoute>
                }
            />
        </Routes>
    );
}

export default App;

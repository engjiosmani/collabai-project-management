import { Routes, Route, Navigate } from "react-router-dom";

import Register from "./pages/Register";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AIAssistant from "./pages/AIAssistant";
import Tasks from "./pages/Tasks";
import Projects from "./pages/Projects";
import Organizations from "./pages/Organizations";
import OrganizationDetail from "./pages/OrganizationDetail";
import WorkspaceDetail from "./pages/WorkspaceDetail";
import Invitations from "./pages/Invitations";
import AcceptInvite from "./pages/AcceptInvite";
import NotificationsPage from "./pages/NotificationsPage";
import ProfilePage from "./pages/ProfilePage";
import SettingsPage from "./pages/settings/SettingsPage";
import ForgotPasswordPage from "./pages/settings/ForgotPasswordPage";
import ResetPasswordPage from "./pages/settings/ResetPasswordPage";
import NotFoundPage from "./pages/errors/NotFoundPage";
import UnauthorizedPage from "./pages/errors/UnauthorizedPage";
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
                    path="/forgot-password"
                    element={<ForgotPasswordPage />}
                />

                <Route
                    path="/reset-password"
                    element={<ResetPasswordPage />}
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
                    path="/tasks"
                    element={
                        <ProtectedRoute>
                            <Tasks />
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
                        <ProtectedRoute>
                            <Organizations />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/organizations/:id"
                    element={
                        <ProtectedRoute>
                            <OrganizationDetail />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/organizations/:orgId/workspaces/:wsId"
                    element={
                        <ProtectedRoute>
                            <WorkspaceDetail />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/invitations"
                    element={
                        <ProtectedRoute>
                            <Invitations />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/profile"
                    element={
                        <ProtectedRoute>
                            <ProfilePage />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/notifications"
                    element={
                        <ProtectedRoute>
                            <NotificationsPage />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/accept-invite/:token"
                    element={<AcceptInvite />}
                />

                <Route
                    path="/settings"
                    element={
                        <ProtectedRoute>
                            <SettingsPage />
                        </ProtectedRoute>
                    }
                />

                <Route path="/404" element={<NotFoundPage />} />

                <Route path="/unauthorized" element={<UnauthorizedPage />} />

                <Route path="*" element={<NotFoundPage />} />
            </Routes>
        </>
    );
}

export default App;

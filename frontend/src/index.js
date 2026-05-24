import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

import { BrowserRouter } from "react-router-dom";
import AppErrorBoundary from "./components/errors/AppErrorBoundary";
import { AuthProvider } from "./context/AuthContext";
import { OrganizationProvider } from "./context/OrganizationContext";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <AppErrorBoundary>
      <AuthProvider>
        <OrganizationProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </OrganizationProvider>
      </AuthProvider>
    </AppErrorBoundary>
  </React.StrictMode>
);

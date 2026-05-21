import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { OrganizationProvider } from "./context/OrganizationContext";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <AuthProvider>
      <OrganizationProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </OrganizationProvider>
    </AuthProvider>
  </React.StrictMode>
);
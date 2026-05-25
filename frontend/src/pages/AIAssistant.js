import { useEffect, useState } from "react";

import API from "../api/api";

import AIAssistantChat from "../components/AIAssistantChat";
import AppSidebar from "../components/AppSidebar";

import "./Dashboard.css";
import "./AIAssistant.css";

function AIAssistant() {
  const [redisWarning, setRedisWarning] = useState(false);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const checkHealth = async () => {
      try {
        const response = await API.get("/api/v1/health/");

        if (
          response.data.cache === "locmem" ||
          response.data.vector_store === "memory"
        ) {
          setRedisWarning(true);
        }
      } catch (error) {
        console.error("Health check failed:", error);
      }
    };

    checkHealth();

    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main">
        {redisWarning && (
          <div
            style={{
              background: "#fff3cd",
              color: "#856404",
              padding: "12px",
              borderRadius: "8px",
              marginBottom: "16px",
              border: "1px solid #ffeeba",
              fontWeight: "600",
            }}
          >
            System notice: AI knowledge may reset after a server restart.
          </div>
        )}

        <AIAssistantChat variant="page" />
      </main>
    </div>
  );
}

export default AIAssistant;

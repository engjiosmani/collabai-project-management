import { useEffect } from "react";

import AIAssistantChat from "../components/AIAssistantChat";
import AppSidebar from "../components/AppSidebar";

import "./Dashboard.css";
import "./AIAssistant.css";

function AIAssistant() {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main">
        <AIAssistantChat variant="page" />
      </main>
    </div>
  );
}

export default AIAssistant;

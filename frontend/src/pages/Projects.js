import { useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import AppSidebar from "../components/AppSidebar";
import ProjectsPanel from "../components/ProjectsPanel";

import "./Dashboard.css";
import "./AIAssistant.css";
import "./Projects.css";

function Projects() {
    const navigate = useNavigate();

    useEffect(() => {
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = prev;
        };
    }, []);

    const handleSelectProject = useCallback(
        (projectId) => {
            if (!projectId) {
                navigate("/dashboard", { state: { scrollTo: "tasks" } });
                return;
            }
            navigate(`/dashboard?project=${encodeURIComponent(String(projectId))}`, {
                state: { scrollTo: "tasks" },
            });
        },
        [navigate]
    );

    return (
        <div className="dashboard-shell dashboard-shell--viewport">
            <AppSidebar />

            <main className="ai-main projects-main">
                <header className="ai-topbar">
                    <div>
                        <h2 className="ai-heading">Your projects</h2>
                        <p className="projects-page-lead">
                            Browse workspace projects and open tasks on the Kanban board.
                        </p>
                    </div>
                </header>

                <div className="projects-page-body">
                    <ProjectsPanel layout="page" onSelectProject={handleSelectProject} />
                </div>
            </main>
        </div>
    );
}

export default Projects;

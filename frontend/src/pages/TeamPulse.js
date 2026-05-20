import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchProjects } from "../api/projects";
import {
  fetchOrganizationMembers,
  fetchTeamPulseOverview,
  getApiErrorMessage,
  runTeamPulse,
  saveGitHubConfig,
} from "../api/teamPulse";
import StandupMarkdown from "../components/teamPulse/StandupMarkdown";
import AppSidebar from "../components/AppSidebar";
import TeamPulseGitHubSetup, {
  getGitHubSetupStatus,
} from "../components/teamPulse/TeamPulseGitHubSetup";

import "./Dashboard.css";
import "./AIAssistant.css";
import "./TeamPulse.css";

function TeamPulse() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubRepos, setGithubRepos] = useState("");
  const [githubEnabled, setGithubEnabled] = useState(false);
  const [members, setMembers] = useState([]);
  const [githubLogins, setGithubLogins] = useState({});
  const [showGitHubSettings, setShowGitHubSettings] = useState(false);

  const selectedProject = useMemo(
    () => projects.find((p) => String(p.id) === projectId),
    [projects, projectId]
  );
  const organizationId = selectedProject?.organization;

  useEffect(() => {
    (async () => {
      try {
        const list = await fetchProjects();
        setProjects(list);
        if (list.length) setProjectId(String(list[0].id));
      } catch (err) {
        setError(getApiErrorMessage(err, "Could not load projects."));
      }
    })();
  }, []);

  const load = useCallback(async () => {
    if (!organizationId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchTeamPulseOverview(organizationId);
      setOverview(data);
      const gh = data.github;
      if (gh) {
        setGithubRepos((gh.repos || []).join("\n"));
        setGithubEnabled(Boolean(gh.is_enabled));
        setGithubLogins(gh.member_github_logins || {});
      } else {
        setGithubRepos("");
        setGithubEnabled(false);
        setGithubLogins({});
      }
      try {
        const memberList = await fetchOrganizationMembers(organizationId);
        setMembers(Array.isArray(memberList) ? memberList : []);
      } catch {
        setMembers([]);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not load Team Pulse."));
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    load();
  }, [load]);

  const standup = overview?.latest_standup;
  const repos = githubRepos
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const mappedMembers = members.filter((m) => (githubLogins[String(m.user)] || "").trim()).length;
  const githubStatus = getGitHubSetupStatus({
    overview,
    githubRepos,
    githubEnabled,
    githubLogins,
    members,
  });
  const lastRun = standup?.created_at
    ? new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(standup.created_at))
    : "Not run";

  const handleSaveGitHub = async (e) => {
    e.preventDefault();
    if (!organizationId) return;
    setError("");
    try {
      await saveGitHubConfig({
        organization_id: Number(organizationId),
        access_token: githubToken || undefined,
        repos,
        is_enabled: githubEnabled,
        member_github_logins: githubLogins,
      });
      setGithubToken("");
      await load();
      setShowGitHubSettings(false);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not save GitHub settings."));
    }
  };

  const handleRunStandup = async () => {
    if (!organizationId) return;
    setRunning(true);
    setError("");
    try {
      await runTeamPulse(Number(organizationId), "standup");
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, "Run failed."));
    } finally {
      setRunning(false);
    }
  };

  const shouldShowSettings = showGitHubSettings || githubStatus.level !== "ready";

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main tp-main">
        <header className="tp-page-header">
          <div className="tp-page-header__intro">
            <h2 className="tp-page-title">Team Pulse</h2>
            <p className="tp-lead">Daily standup, blockers, and commit activity.</p>
          </div>
          <div className="tp-page-header__controls">
            <label className="tp-workspace-field">
              <span className="tp-workspace-label">Project</span>
              <select
                className="tp-workspace-select"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                aria-label="Project"
                disabled={projects.length === 0}
              >
                {projects.length === 0 ? (
                  <option value="">No project</option>
                ) : (
                  projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))
                )}
              </select>
            </label>
            <button
              type="button"
              className="dashboard-button dashboard-button--primary tp-run-all-btn"
              disabled={running || !projectId}
              onClick={handleRunStandup}
            >
              {running ? "Running..." : "Generate"}
            </button>
          </div>
        </header>

        {error ? (
          <div className="ai-error" role="alert">
            {error}
          </div>
        ) : null}

        <section className="tp-snapshot" aria-label="Team Pulse status">
          <article className="tp-snapshot-card">
            <span className="tp-snapshot-label">Last run</span>
            <strong>{lastRun}</strong>
          </article>
          <article className="tp-snapshot-card">
            <span className="tp-snapshot-label">GitHub</span>
            <strong>{githubStatus.level === "ready" ? "Connected" : "Needs setup"}</strong>
          </article>
          <article className="tp-snapshot-card">
            <span className="tp-snapshot-label">Members</span>
            <strong>{members.length ? `${mappedMembers}/${members.length} mapped` : "No members"}</strong>
          </article>
        </section>

        <section className="tp-setup-strip" aria-label="GitHub setup summary">
          <div className="tp-setup-strip__main">
            <span className={`tp-status-dot tp-status-dot--${githubStatus.level}`} aria-hidden />
            <div>
              <strong>GitHub commits</strong>
              <span>
                {repos.length} repo{repos.length === 1 ? "" : "s"} -{" "}
                {githubEnabled ? "sync on" : "sync off"}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="dashboard-button dashboard-button--ghost"
            onClick={() => setShowGitHubSettings((value) => !value)}
          >
            {shouldShowSettings ? "Hide settings" : "Settings"}
          </button>
        </section>

        {shouldShowSettings ? (
          <form className="tp-github-form" onSubmit={handleSaveGitHub}>
            <TeamPulseGitHubSetup
              overview={overview}
              githubToken={githubToken}
              setGithubToken={setGithubToken}
              githubRepos={githubRepos}
              setGithubRepos={setGithubRepos}
              githubEnabled={githubEnabled}
              setGithubEnabled={setGithubEnabled}
              githubLogins={githubLogins}
              setGithubLogins={setGithubLogins}
              members={members}
            />
            <div className="tp-github-form-footer">
              <button type="submit" className="dashboard-button dashboard-button--primary">
                Save settings
              </button>
            </div>
          </form>
        ) : null}

        {loading ? <p className="tp-muted">Loading...</p> : null}

        {!loading ? (
          <section className="tp-card tp-standup-card">
            <div className="tp-card-head">
              <h3 className="tp-card-title">Daily standup</h3>
              <button
                type="button"
                className="dashboard-button dashboard-button--ghost"
                disabled={running}
                onClick={handleRunStandup}
              >
                Generate
              </button>
            </div>
            {standup ? (
              <StandupMarkdown text={standup.summary_markdown} />
            ) : (
              <div className="tp-empty-state">
                <strong>No standup yet</strong>
                <button
                  type="button"
                  className="dashboard-button dashboard-button--primary"
                  disabled={running || !projectId}
                  onClick={handleRunStandup}
                >
                  Generate now
                </button>
              </div>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default TeamPulse;

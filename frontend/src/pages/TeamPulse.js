import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchProjects } from "../api/projects";
import { fetchOrganizationMembers } from "../api/taskGenerator";
import {
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

const FEATURES = [
  {
    icon: "📋",
    title: "Daily standup",
    desc: "Every morning at 9:00: tasks (24h), comments, GitHub commits → yesterday / today / blockers per member.",
    run: "standup",
    runLabel: "Generate standup",
  },
  {
    icon: "🔗",
    title: "GitHub commits",
    desc: "Optional. Pulls recent commits into standups when you connect a token and repos below.",
    run: null,
    runLabel: null,
  },
];

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

  const githubStatus = getGitHubSetupStatus({
    overview,
    githubRepos,
    githubEnabled,
    githubLogins,
    members,
  });

  const handleSaveGitHub = async (e) => {
    e.preventDefault();
    if (!organizationId) return;
    setError("");
    try {
      const repos = githubRepos
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      await saveGitHubConfig({
        organization_id: Number(organizationId),
        access_token: githubToken || undefined,
        repos,
        is_enabled: githubEnabled,
        member_github_logins: githubLogins,
      });
      setGithubToken("");
      await load();
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

  const standup = overview?.latest_standup;

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main tp-main">
        <header className="tp-page-header">
          <div className="tp-page-header__intro">
            <h2 className="tp-page-title">Team Pulse</h2>
            <p className="tp-lead">
              Autonomous daily standup: what each teammate did yesterday, plans for today, and
              blockers — from tasks, comments, and optional GitHub commits.
            </p>
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
              title="Generate today's standup now"
            >
              {running ? "Running…" : "Generate standup"}
            </button>
          </div>
        </header>

        {error ? (
          <div className="ai-error" role="alert">
            {error}
          </div>
        ) : null}

        <section className="tp-features" aria-label="What Team Pulse does">
          {FEATURES.map((f) => (
            <article key={f.title} className="tp-feature-card">
              <span className="tp-feature-icon" aria-hidden>
                {f.icon}
              </span>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
              {f.run ? (
                <button
                  type="button"
                  className="dashboard-button dashboard-button--ghost tp-feature-btn"
                  disabled={running || !projectId}
                  onClick={handleRunStandup}
                >
                  {running ? "…" : f.runLabel}
                </button>
              ) : (
                <span className="tp-feature-meta">
                  {githubStatus.level === "ready" ? "Configured" : "Set up below"}
                </span>
              )}
            </article>
          ))}
        </section>

        <p className="tp-schedule-note">
          <strong>Automatic run:</strong> standup around 9:00 AM (server time). Use the button above
          anytime for an immediate refresh. Reports appear below in the app.
        </p>

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
            <p className="tp-hint">
              Save after each step. Your token is stored securely for this project&apos;s team.
            </p>
            <button type="submit" className="dashboard-button dashboard-button--primary">
              Save GitHub settings
            </button>
          </div>
        </form>

        {loading ? <p className="tp-muted">Loading reports…</p> : null}

        {!loading ? (
          <section className="tp-card tp-standup-card">
            <div className="tp-card-head">
              <div>
                <h3 className="tp-card-title">Daily standup</h3>
                <p className="tp-card-desc tp-card-desc--tight">
                  Yesterday / today / blockers from tasks{githubEnabled ? " and GitHub" : ""}.
                </p>
              </div>
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
              <p className="tp-muted">
                No standup yet. Connect GitHub above (optional), then click Generate or wait for the
                9:00 AM run.
              </p>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default TeamPulse;

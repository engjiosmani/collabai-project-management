import { useCallback, useEffect, useState } from "react";

import { fetchWorkspaces } from "../api/ai";
import { fetchWorkspaceMembers } from "../api/taskGenerator";
import {
  dismissTeamPulseAlert,
  fetchTeamPulseOverview,
  getApiErrorMessage,
  runTeamPulse,
  saveGitHubConfig,
} from "../api/teamPulse";
import AppSidebar from "../components/AppSidebar";
import TeamPulseGitHubSetup, {
  getGitHubSetupStatus,
} from "../components/teamPulse/TeamPulseGitHubSetup";
import { formatWorkspaceLabel } from "../utils/workspaceLabel";

import "./Dashboard.css";
import "./AIAssistant.css";
import "./TeamPulse.css";

const FEATURES = [
  {
    icon: "⚖️",
    title: "Workload balance",
    desc: "Spots uneven task load and suggests who could take more work or needs help.",
    run: "workload",
    runLabel: "Analyze workload",
  },
  {
    icon: "📋",
    title: "Daily standup",
    desc: "Summarizes what the team did yesterday, plans for today, and blockers from tasks and GitHub.",
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
  const [workspaces, setWorkspaces] = useState([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubRepos, setGithubRepos] = useState("");
  const [githubEnabled, setGithubEnabled] = useState(false);
  const [members, setMembers] = useState([]);
  const [githubLogins, setGithubLogins] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const list = await fetchWorkspaces();
        setWorkspaces(list);
        if (list.length) setWorkspaceId(String(list[0].id));
      } catch (err) {
        setError(getApiErrorMessage(err, "Could not load workspaces."));
      }
    })();
  }, []);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchTeamPulseOverview(workspaceId);
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
        const memberList = await fetchWorkspaceMembers(workspaceId);
        setMembers(Array.isArray(memberList) ? memberList : []);
      } catch {
        setMembers([]);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not load Team Pulse."));
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

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
    if (!workspaceId) return;
    setError("");
    try {
      const repos = githubRepos
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      await saveGitHubConfig({
        workspace_id: Number(workspaceId),
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

  const handleRun = async (runType) => {
    if (!workspaceId) return;
    setRunning(true);
    setError("");
    try {
      await runTeamPulse(Number(workspaceId), runType);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, "Run failed."));
    } finally {
      setRunning(false);
    }
  };

  const handleDismiss = async (alertId) => {
    try {
      await dismissTeamPulseAlert(alertId);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not dismiss alert."));
    }
  };

  const standup = overview?.latest_standup;
  const workload = overview?.latest_workload;
  const alerts = overview?.alerts || [];

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main tp-main">
        <header className="tp-page-header">
          <div className="tp-page-header__intro">
            <h2 className="tp-page-title">Team Pulse</h2>
            <p className="tp-lead">
              AI checks how work is spread across your team, flags burnout risk, and builds a daily
              standup — optionally enriched with GitHub commits.
            </p>
          </div>
          <div className="tp-page-header__controls">
            <label className="tp-workspace-field">
              <span className="tp-workspace-label">Workspace</span>
              <select
                className="tp-workspace-select"
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                aria-label="Workspace"
                disabled={workspaces.length === 0}
              >
                {workspaces.length === 0 ? (
                  <option value="">No workspace</option>
                ) : (
                  workspaces.map((ws) => (
                    <option key={ws.id} value={ws.id}>
                      {formatWorkspaceLabel(ws)}
                    </option>
                  ))
                )}
              </select>
            </label>
            <button
              type="button"
              className="dashboard-button dashboard-button--primary tp-run-all-btn"
              disabled={running || !workspaceId}
              onClick={() => handleRun("both")}
              title="Runs workload analysis and generates today's standup"
            >
              {running ? "Running…" : "Run everything"}
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
                  disabled={running || !workspaceId}
                  onClick={() => handleRun(f.run)}
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
          <strong>Automatic runs:</strong> workload analysis around 2:00 AM, standup around 9:00 AM
          (server time). Use the buttons above anytime for an immediate refresh.
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
              Save after each step. Your token is stored securely for this workspace only.
            </p>
            <button type="submit" className="dashboard-button dashboard-button--primary">
              Save GitHub settings
            </button>
          </div>
        </form>

        {loading ? <p className="tp-muted">Loading reports…</p> : null}

        {!loading && alerts.length > 0 ? (
          <section className="tp-card">
            <h3 className="tp-card-title">Workload alerts</h3>
            <p className="tp-card-desc">Active suggestions from the latest workload analysis.</p>
            <ul className="tp-alert-list">
              {alerts.map((a) => (
                <li key={a.id} className={`tp-alert tp-alert--${a.severity}`}>
                  <div>
                    <strong>{a.title}</strong>
                    <p>{a.message}</p>
                  </div>
                  <button
                    type="button"
                    className="dashboard-button dashboard-button--ghost"
                    onClick={() => handleDismiss(a.id)}
                  >
                    Dismiss
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {!loading && alerts.length === 0 ? (
          <p className="tp-muted tp-results-hint">
            No active workload alerts. Run <strong>Analyze workload</strong> to refresh.
          </p>
        ) : null}

        <div className="tp-grid">
          <section className="tp-card">
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
                onClick={() => handleRun("standup")}
              >
                Generate
              </button>
            </div>
            {standup ? (
              <pre className="tp-pre">{standup.summary_markdown || "No content"}</pre>
            ) : (
              <p className="tp-muted">
                No standup yet. Connect GitHub above (optional), then click Generate or wait for the
                9:00 AM run.
              </p>
            )}
          </section>

          <section className="tp-card">
            <div className="tp-card-head">
              <div>
                <h3 className="tp-card-title">Workload snapshot</h3>
                <p className="tp-card-desc tp-card-desc--tight">
                  Who is overloaded, who has capacity, and suggested reassignments.
                </p>
              </div>
              <button
                type="button"
                className="dashboard-button dashboard-button--ghost"
                disabled={running}
                onClick={() => handleRun("workload")}
              >
                Analyze
              </button>
            </div>
            {workload ? (
              <pre className="tp-pre">{workload.summary_markdown || "No content"}</pre>
            ) : (
              <p className="tp-muted">
                No analysis yet. Click Analyze or wait for the nightly 2:00 AM run.
              </p>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

export default TeamPulse;

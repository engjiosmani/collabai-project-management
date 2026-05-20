import { useMemo } from "react";

const GITHUB_PAT_URL = "https://github.com/settings/personal-access-tokens/new";

function parseRepos(text) {
  return text
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function getGitHubSetupStatus({ overview, githubRepos, githubEnabled, githubLogins, members }) {
  const gh = overview?.github;
  const repos = parseRepos(githubRepos);
  const hasToken = Boolean(gh?.has_token);
  const mappedCount = members.filter((m) => (githubLogins[String(m.user)] || "").trim()).length;
  const membersReady = members.length === 0 || mappedCount === members.length;

  if (!hasToken) return { level: "todo", label: "Token missing" };
  if (!repos.length) return { level: "todo", label: "No repos" };
  if (!membersReady) return { level: "todo", label: `${mappedCount}/${members.length} mapped` };
  if (!githubEnabled) return { level: "todo", label: "Sync off" };
  return { level: "ready", label: "Connected" };
}

function TeamPulseGitHubSetup({
  overview,
  githubToken,
  setGithubToken,
  githubRepos,
  setGithubRepos,
  githubEnabled,
  setGithubEnabled,
  githubLogins,
  setGithubLogins,
  members,
}) {
  const status = useMemo(
    () =>
      getGitHubSetupStatus({
        overview,
        githubRepos,
        githubEnabled,
        githubLogins,
        members,
      }),
    [overview, githubRepos, githubEnabled, githubLogins, members]
  );

  const hasToken = Boolean(overview?.github?.has_token);
  const repos = parseRepos(githubRepos);

  return (
    <section className="tp-card tp-github">
      <div className="tp-github-head">
        <h3 className="tp-card-title">GitHub settings</h3>
        <span className={`tp-status-pill tp-status-pill--${status.level}`}>{status.label}</span>
      </div>

      <details className="tp-token-help">
        <summary>How to get a GitHub token</summary>
        <ol>
          <li>
            Open{" "}
            <a href={GITHUB_PAT_URL} target="_blank" rel="noopener noreferrer">
              GitHub token settings
            </a>
            .
          </li>
          <li>Name it CollabAI Team Pulse.</li>
          <li>Select the repositories CollabAI should read.</li>
          <li>Set Contents to Read-only, then generate and copy the token.</li>
          <li>Paste the token here. It starts with github_pat_.</li>
        </ol>
      </details>

      <div className="tp-compact-grid">
        <label className="tp-label">
          Token
          <input
            type="password"
            className="tp-input"
            placeholder={hasToken ? "Saved - leave blank" : "github_pat_... or ghp_..."}
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            autoComplete="off"
          />
        </label>

        <label className="tp-checkbox tp-sync-toggle">
          <input
            type="checkbox"
            checked={githubEnabled}
            onChange={(e) => setGithubEnabled(e.target.checked)}
          />
          Include commits
        </label>
      </div>

      <label className="tp-label">
        Repositories
        <textarea
          className="tp-input tp-textarea tp-repo-textarea"
          rows={3}
          value={githubRepos}
          onChange={(e) => setGithubRepos(e.target.value)}
          placeholder={"owner/repo\nowner/frontend"}
        />
      </label>

      {repos.length ? (
        <ul className="tp-repo-chips" aria-label="Configured repositories">
          {repos.map((repo) => (
            <li key={repo}>{repo}</li>
          ))}
        </ul>
      ) : null}

      {members.length ? (
        <div className="tp-member-map">
          <span className="tp-label-text">GitHub users</span>
          <ul className="tp-member-list">
            {members.map((member) => (
              <li key={member.id}>
                <label className="tp-member-row">
                  <span className="tp-member-email">{member.user_email || `User #${member.user}`}</span>
                  <input
                    type="text"
                    className="tp-input"
                    placeholder="username"
                    value={githubLogins[String(member.user)] || ""}
                    onChange={(e) =>
                      setGithubLogins((prev) => ({
                        ...prev,
                        [String(member.user)]: e.target.value.trim(),
                      }))
                    }
                  />
                </label>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

export default TeamPulseGitHubSetup;

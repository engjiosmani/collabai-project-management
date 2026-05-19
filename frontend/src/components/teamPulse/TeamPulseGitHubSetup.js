import { useMemo, useState } from "react";

const GITHUB_NEW_TOKEN_URL = "https://github.com/settings/personal-access-tokens/new";
const GITHUB_CLASSIC_TOKEN_URL = "https://github.com/settings/tokens/new?scopes=repo";

function parseRepos(text) {
  return text
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function repoFromGithubUrl(url) {
  try {
    const match = url.trim().match(/github\.com\/([^/]+)\/([^/#?]+)/i);
    if (match) return `${match[1]}/${match[2].replace(/\.git$/, "")}`;
  } catch {
    /* ignore */
  }
  return "";
}

export function getGitHubSetupStatus({ overview, githubRepos, githubEnabled, githubLogins, members }) {
  const gh = overview?.github;
  const repos = parseRepos(githubRepos);
  const hasToken = Boolean(gh?.has_token);
  const hasRepos = repos.length > 0;
  const needsMemberMap = members.length > 0;
  const mappedCount = needsMemberMap
    ? members.filter((m) => (githubLogins[String(m.user)] || "").trim()).length
    : members.length;
  const membersReady = !needsMemberMap || mappedCount === members.length;

  if (!hasToken) {
    return { level: "todo", step: 1, label: "Add a GitHub token to get started" };
  }
  if (!hasRepos) {
    return { level: "todo", step: 2, label: "Add at least one repository" };
  }
  if (!membersReady) {
    return {
      level: "todo",
      step: 3,
      label: `Map GitHub usernames (${mappedCount}/${members.length} done)`,
    };
  }
  if (!githubEnabled) {
    return { level: "todo", step: 4, label: "Turn on commit sync and save" };
  }
  return {
    level: "ready",
    step: 0,
    label: `Connected · ${repos.length} repo${repos.length === 1 ? "" : "s"}`,
  };
}

function StepBadge({ number, done, active }) {
  const cls = ["tp-step-badge"];
  if (done) cls.push("tp-step-badge--done");
  if (active) cls.push("tp-step-badge--active");
  return (
    <span className={cls.join(" ")} aria-hidden>
      {done ? "✓" : number}
    </span>
  );
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

  const [openStep, setOpenStep] = useState(() => status.step || 1);
  const [repoPasteUrl, setRepoPasteUrl] = useState("");

  const gh = overview?.github;
  const repos = parseRepos(githubRepos);
  const hasToken = Boolean(gh?.has_token);
  const step1Done = hasToken;
  const step2Done = repos.length > 0;
  const mappedCount = members.filter((m) => (githubLogins[String(m.user)] || "").trim()).length;
  const step3Done = members.length === 0 || mappedCount === members.length;
  const step4Done = githubEnabled && step1Done && step2Done && step3Done;

  const toggleStep = (n) => setOpenStep((prev) => (prev === n ? 0 : n));

  const addRepoFromUrl = () => {
    const slug = repoFromGithubUrl(repoPasteUrl);
    if (!slug) return;
    setGithubRepos((prev) => {
      const existing = parseRepos(prev);
      if (existing.includes(slug)) return prev;
      return [...existing, slug].join("\n");
    });
    setRepoPasteUrl("");
  };

  return (
    <section className="tp-card tp-github">
      <div className="tp-github-head">
        <div>
          <h3 className="tp-card-title">GitHub setup</h3>
          <p className="tp-card-desc tp-card-desc--tight">
            Team Pulse reads <strong>commit history</strong> from your repos and adds it to the daily
            standup. Nothing is posted back to GitHub.
          </p>
        </div>
        <span className={`tp-status-pill tp-status-pill--${status.level}`}>{status.label}</span>
      </div>

      <ol className="tp-steps">
        <li className={`tp-step${openStep === 1 ? " tp-step--open" : ""}`}>
          <button type="button" className="tp-step-trigger" onClick={() => toggleStep(1)}>
            <StepBadge number={1} done={step1Done} active={openStep === 1} />
            <span className="tp-step-title">Create a Personal Access Token (PAT)</span>
          </button>
          {openStep === 1 ? (
            <div className="tp-step-body">
              <div className="tp-callout">
                <p>
                  A PAT is a password-like key that lets CollabAI <strong>read</strong> commits from
                  repositories you choose. Create it once on GitHub, then paste it below.
                </p>
              </div>
              <ol className="tp-guide-list">
                <li>
                  Open{" "}
                  <a href={GITHUB_NEW_TOKEN_URL} target="_blank" rel="noopener noreferrer">
                    GitHub → Settings → Developer settings → Fine-grained tokens → Generate
                  </a>
                  .
                </li>
                <li>
                  <strong>Name</strong> it e.g. <code>CollabAI Team Pulse</code>.
                </li>
                <li>
                  Under <strong>Repository access</strong>, pick only the repos you want in standups
                  (or all repos you use).
                </li>
                <li>
                  Under <strong>Permissions → Repository</strong>, set{" "}
                  <code>Contents</code> and <code>Metadata</code> to <strong>Read-only</strong>.
                </li>
                <li>
                  Generate the token and copy it immediately (GitHub shows it only once). It starts
                  with <code>github_pat_</code>.
                </li>
              </ol>
              <details className="tp-details">
                <summary>Classic token instead? (simpler, broader access)</summary>
                <p>
                  Use a{" "}
                  <a href={GITHUB_CLASSIC_TOKEN_URL} target="_blank" rel="noopener noreferrer">
                    classic token
                  </a>{" "}
                  with the <code>repo</code> scope if fine-grained tokens are confusing. Paste it in
                  the same field below.
                </p>
              </details>
              <label className="tp-label">
                Paste your token here
                <input
                  type="password"
                  className="tp-input"
                  placeholder={hasToken ? "Leave blank to keep current token" : "github_pat_… or ghp_…"}
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  autoComplete="off"
                />
              </label>
              {hasToken ? (
                <p className="tp-hint tp-hint--ok">A token is saved for this workspace.</p>
              ) : (
                <p className="tp-hint">Required before standups can include GitHub activity.</p>
              )}
            </div>
          ) : null}
        </li>

        <li className={`tp-step${openStep === 2 ? " tp-step--open" : ""}`}>
          <button type="button" className="tp-step-trigger" onClick={() => toggleStep(2)}>
            <StepBadge number={2} done={step2Done} active={openStep === 2} />
            <span className="tp-step-title">Tell us which repositories</span>
          </button>
          {openStep === 2 ? (
            <div className="tp-step-body">
              <p className="tp-step-intro">
                Use the format <code>owner/repo</code> — the same as in the GitHub URL.
              </p>
              <div className="tp-example-box">
                <span className="tp-example-label">Example URL</span>
                <code>https://github.com/acme/collabai-backend</code>
                <span className="tp-example-arrow">→</span>
                <code className="tp-example-result">acme/collabai-backend</code>
              </div>
              <div className="tp-repo-paste">
                <input
                  type="url"
                  className="tp-input"
                  placeholder="Paste a GitHub repo URL to add…"
                  value={repoPasteUrl}
                  onChange={(e) => setRepoPasteUrl(e.target.value)}
                />
                <button
                  type="button"
                  className="dashboard-button dashboard-button--ghost"
                  onClick={addRepoFromUrl}
                  disabled={!repoFromGithubUrl(repoPasteUrl)}
                >
                  Add repo
                </button>
              </div>
              <label className="tp-label">
                Repositories (one per line)
                <textarea
                  className="tp-input tp-textarea"
                  rows={4}
                  value={githubRepos}
                  onChange={(e) => setGithubRepos(e.target.value)}
                  placeholder={"acme/collabai-backend\nacme/collabai-frontend"}
                />
              </label>
              {repos.length > 0 ? (
                <ul className="tp-repo-chips">
                  {repos.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </li>

        <li className={`tp-step${openStep === 3 ? " tp-step--open" : ""}`}>
          <button type="button" className="tp-step-trigger" onClick={() => toggleStep(3)}>
            <StepBadge number={3} done={step3Done} active={openStep === 3} />
            <span className="tp-step-title">Match team members to GitHub</span>
          </button>
          {openStep === 3 ? (
            <div className="tp-step-body">
              <p className="tp-step-intro">
                GitHub commits are tied to a <strong>GitHub username</strong>, not an email. Enter each
                person&apos;s login so their commits appear under the right CollabAI account.
              </p>
              <p className="tp-hint">
                Find a username on their GitHub profile: <code>github.com/username</code> — use{" "}
                <code>username</code> only, without <code>@</code>.
              </p>
              {members.length === 0 ? (
                <p className="tp-muted">No workspace members yet. Invite teammates from your workspace settings.</p>
              ) : (
                <ul className="tp-member-list">
                  {members.map((m) => (
                    <li key={m.id}>
                      <label className="tp-member-row">
                        <span className="tp-member-email">{m.user_email || `User #${m.user}`}</span>
                        <input
                          type="text"
                          className="tp-input"
                          placeholder="github-username"
                          value={githubLogins[String(m.user)] || ""}
                          onChange={(e) =>
                            setGithubLogins((prev) => ({
                              ...prev,
                              [String(m.user)]: e.target.value.trim(),
                            }))
                          }
                        />
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </li>

        <li className={`tp-step${openStep === 4 ? " tp-step--open" : ""}`}>
          <button type="button" className="tp-step-trigger" onClick={() => toggleStep(4)}>
            <StepBadge number={4} done={step4Done} active={openStep === 4} />
            <span className="tp-step-title">Enable sync and save</span>
          </button>
          {openStep === 4 ? (
            <div className="tp-step-body">
              <label className="tp-checkbox">
                <input
                  type="checkbox"
                  checked={githubEnabled}
                  onChange={(e) => setGithubEnabled(e.target.checked)}
                />
                Include GitHub commits in daily standups
              </label>
              <p className="tp-hint">
                When enabled, the next standup run will fetch recent commits from the repos above for
                each mapped username. Then click <strong>Save GitHub settings</strong> at the bottom of
                this section.
              </p>
            </div>
          ) : null}
        </li>
      </ol>
    </section>
  );
}

export default TeamPulseGitHubSetup;

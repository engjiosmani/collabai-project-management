import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { fetchProjects } from "../api/projects";
import {
  approveTaskPlan,
  createTaskPlan,
  fetchAIConfig,
  fetchJobRoles,
  fetchTaskPlan,
  fetchTaskPlanStatus,
  fetchOrganizationMembers,
  fetchOrganizationProjects,
  getApiErrorMessage,
  regeneratePlannedTask,
  rejectTaskPlan,
  updateMemberJobRole,
  updatePlannedTask,
} from "../api/taskGenerator";
import AppSidebar from "../components/AppSidebar";
import TaskDescriptionMarkdown from "../components/TaskDescriptionMarkdown";

import "./Dashboard.css";
import "./AIAssistant.css";
import "./TaskGenerator.css";

const GENERATING_STATUSES = new Set(["DRAFT", "GENERATING"]);
const POLL_MS = 2500;

function groupTasksBySprint(tasks) {
  const map = new Map();
  for (const task of tasks || []) {
    const key = task.sprint_number || 1;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(task);
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0]);
}

function membersToTeamPayload(members, selectedIds, jobRoleByMemberId, jobRoles) {
  return members
    .filter((m) => selectedIds.has(m.user))
    .map((m) => {
      const jobRoleId = jobRoleByMemberId[m.id] ?? m.job_role ?? null;
      const jobRole = jobRoles.find((r) => r.id === jobRoleId) || null;
      return {
        user_id: m.user,
        username: m.user_email?.split("@")[0] || `user-${m.user}`,
        role: jobRole?.name || m.job_role_name || "Team Member",
        job_role_code: jobRole?.code || m.job_role_code || null,
        job_role_id: jobRoleId,
        task_categories: jobRole?.task_categories || m.task_categories || [],
      };
    });
}

function TaskGenerator() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [members, setMembers] = useState([]);
  const [jobRoles, setJobRoles] = useState([]);
  const [jobRoleByMemberId, setJobRoleByMemberId] = useState({});
  const [selectedMemberIds, setSelectedMemberIds] = useState(new Set());
  const [projectsLoading, setProjectsLoading] = useState(true);

  const [description, setDescription] = useState("");
  const [sprintCount, setSprintCount] = useState(3);
  const [syncMode, setSyncMode] = useState("new");
  const [targetProjectId, setTargetProjectId] = useState("");
  const [organizationProjects, setOrganizationProjects] = useState([]);

  const [phase, setPhase] = useState("form");
  const [planId, setPlanId] = useState(null);
  const [plan, setPlan] = useState(null);
  const [genStatus, setGenStatus] = useState("GENERATING");

  const [error, setError] = useState("");
  const [groqConfigured, setGroqConfigured] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const [previewTask, setPreviewTask] = useState(null);
  const [editTask, setEditTask] = useState(null);
  const [regenHint, setRegenHint] = useState("");
  const [syncResult, setSyncResult] = useState(null);

  const selectedProject = projects.find((p) => String(p.id) === projectId);
  const orgId = selectedProject?.organization ? Number(selectedProject.organization) : null;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setProjectsLoading(true);
      try {
        const [list, roles] = await Promise.all([fetchProjects(), fetchJobRoles()]);
        if (cancelled) return;
        setProjects(list);
        setJobRoles(roles);
        if (list.length > 0) setProjectId(String(list[0].id));

        try {
          const aiConfig = await fetchAIConfig();
          if (cancelled) return;
          setGroqConfigured(Boolean(aiConfig.groq_configured));
          if (!aiConfig.groq_configured) {
            setError(
              aiConfig.hint ||
                "GROQ_API_KEY is missing on the backend. Add it to backend/.env and restart runserver."
            );
          }
        } catch (configErr) {
          if (cancelled) return;
          const status = configErr.response?.status;
          if (status === 503) {
            setGroqConfigured(false);
            setError(getApiErrorMessage(configErr));
          } else if (status === 401) {
            setGroqConfigured(null);
            setError("Session expired. Please log in again.");
          } else {
            // Do not block generation if config check failed (e.g. old backend)
            setGroqConfigured(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(getApiErrorMessage(err, "Could not load projects."));
        }
      } finally {
        if (!cancelled) setProjectsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!orgId) {
      setMembers([]);
      setSelectedMemberIds(new Set());
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchOrganizationMembers(orgId);
        if (cancelled) return;
        setMembers(list);
        setSelectedMemberIds(new Set(list.map((m) => m.user)));
        const roleMap = {};
        for (const m of list) {
          roleMap[m.id] = m.job_role ?? null;
        }
        setJobRoleByMemberId(roleMap);
      } catch {
        if (!cancelled) setMembers([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  useEffect(() => {
    if (!orgId) {
      setOrganizationProjects([]);
      setTargetProjectId("");
      return undefined;
    }
    let cancelled = false;
    (async () => {
      setProjectsLoading(true);
      try {
        const list = await fetchOrganizationProjects(orgId);
        if (!cancelled) {
          setOrganizationProjects(list);
          if (syncMode === "existing" && list.length > 0 && !targetProjectId) {
            setTargetProjectId(String(list[0].id));
          }
        }
      } catch {
        if (!cancelled) setOrganizationProjects([]);
      } finally {
        if (!cancelled) setProjectsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orgId, syncMode, targetProjectId]);

  const handleSyncModeChange = (mode) => {
    setSyncMode(mode);
    if (mode === "existing" && organizationProjects.length > 0) {
      setTargetProjectId(String(organizationProjects[0].id));
    } else if (mode === "new") {
      setTargetProjectId("");
    }
  };

  const applyPlanTargetFromServer = useCallback((data) => {
    if (data?.target_project_id) {
      setSyncMode("existing");
      setTargetProjectId(String(data.target_project_id));
    }
  }, []);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const loadPlan = useCallback(async (id) => {
    const data = await fetchTaskPlan(id);
    setPlan(data);
    applyPlanTargetFromServer(data);
    return data;
  }, [applyPlanTargetFromServer]);

  useEffect(() => {
    if (phase !== "generating" || !planId) return undefined;

    let cancelled = false;

    const poll = async () => {
      try {
        const statusData = await fetchTaskPlanStatus(planId);
        if (cancelled) return;
        setGenStatus(statusData.status);

        if (statusData.status === "PENDING_APPROVAL") {
          await loadPlan(planId);
          if (!cancelled) {
            setPhase("review");
            setError("");
          }
        } else if (statusData.status === "FAILED") {
          if (!cancelled) {
            setError(
              statusData.error_message ||
                "Plan generation failed. Try a shorter description or fewer sprints."
            );
            setPhase("form");
          }
        } else if (statusData.status === "SYNCED") {
          await loadPlan(planId);
          if (!cancelled) setPhase("synced");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || "Could not check plan status.");
        }
      }
    };

    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [phase, planId, loadPlan]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!orgId || !description.trim()) return;

    const team = membersToTeamPayload(members, selectedMemberIds, jobRoleByMemberId, jobRoles);
    if (team.length === 0) {
      setError("Select at least one team member.");
      return;
    }
    if (syncMode === "existing" && !targetProjectId) {
      setError("Select an existing project to add tasks to.");
      return;
    }
    if (syncMode === "existing" && organizationProjects.length === 0) {
      setError("No projects in this workspace. Create a project on the Dashboard first, or choose “New project”.");
      return;
    }

    setSubmitting(true);
    setError("");
    setSyncResult(null);

    try {
      const res = await createTaskPlan({
        organizationId: orgId,
        description: description.trim(),
        sprintCount: Number(sprintCount),
        teamMembers: team,
        targetProjectId:
          syncMode === "existing" && targetProjectId ? Number(targetProjectId) : null,
      });
      if (res.status === "FAILED" || res.detail?.includes("Groq")) {
        setError(res.detail || "Plan generation failed.");
        return;
      }
      setPlanId(res.plan_id);
      setGenStatus(res.status || "GENERATING");
      if (res.status === "PENDING_APPROVAL") {
        await loadPlan(res.plan_id);
        setPhase("review");
        setError("");
        return;
      }
      setPhase("generating");
      setError("");
    } catch (err) {
      setError(
        getApiErrorMessage(err, "Could not start plan generation.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!planId) return;
    if (syncMode === "existing" && !targetProjectId) {
      setError("Select an existing project to add tasks to.");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      const res = await approveTaskPlan(planId, {
        targetProjectId:
          syncMode === "existing" ? Number(targetProjectId) : null,
      });
      setSyncResult(res);
      await loadPlan(planId);
      setPhase("synced");
    } catch (err) {
      setError(getApiErrorMessage(err, "Approve failed."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!planId || !window.confirm("Discard this plan? It cannot be recovered.")) return;
    setActionLoading(true);
    try {
      await rejectTaskPlan(planId);
      setPlanId(null);
      setPlan(null);
      setPhase("form");
    } catch (err) {
      setError(err.response?.data?.detail || "Reject failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegenerateTask = async (task) => {
    if (!planId) return;
    setActionLoading(true);
    setError("");
    try {
      const updated = await regeneratePlannedTask(planId, task.id, regenHint);
      setPlan((prev) => ({
        ...prev,
        planned_tasks: prev.planned_tasks.map((t) =>
          t.id === updated.id ? updated : t
        ),
      }));
      setPreviewTask(updated);
      setRegenHint("");
    } catch (err) {
      setError(err.response?.data?.detail || "Regenerate failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!planId || !editTask) return;
    setActionLoading(true);
    try {
      const updated = await updatePlannedTask(planId, editTask.id, {
        title: editTask.title,
        goal: editTask.goal,
        description: editTask.description,
        story_points: editTask.story_points,
      });
      setPlan((prev) => ({
        ...prev,
        planned_tasks: prev.planned_tasks.map((t) =>
          t.id === updated.id ? updated : t
        ),
      }));
      setEditTask(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Save failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const sprintGroups = useMemo(
    () => groupTasksBySprint(plan?.planned_tasks),
    [plan]
  );

  const warnings = plan?.validation_meta?.warnings || [];
  const missingThemes = plan?.validation_meta?.missing_themes || [];

  const selectedProjectName =
    organizationProjects.find((p) => String(p.id) === String(targetProjectId))?.name ||
    plan?.target_project_name ||
    "";

  const syncTargetPanel = (
    <div className="tg-sync-target">
      <span className="tg-label">When you approve</span>
      <div className="tg-sync-mode" role="radiogroup" aria-label="Project target">
        <label className="tg-sync-option">
          <input
            type="radio"
            name="tg-sync-mode"
            value="new"
            checked={syncMode === "new"}
            onChange={() => handleSyncModeChange("new")}
            disabled={actionLoading || submitting}
          />
          <span>
            <strong>Create new project</strong>
            <small>AI project name becomes a new project in this workspace</small>
          </span>
        </label>
        <label className="tg-sync-option">
          <input
            type="radio"
            name="tg-sync-mode"
            value="existing"
            checked={syncMode === "existing"}
            onChange={() => handleSyncModeChange("existing")}
            disabled={actionLoading || submitting || projectsLoading}
          />
          <span>
            <strong>Add to existing project</strong>
            <small>Only new tasks are created; the project stays as-is</small>
          </span>
        </label>
      </div>
      {syncMode === "existing" ? (
        <div className="tg-sync-project-pick">
          <label className="tg-label" htmlFor="tg-target-project">
            Project
          </label>
          {projectsLoading ? (
            <p className="tg-regen-hint">Loading projects…</p>
          ) : organizationProjects.length === 0 ? (
            <p className="tg-regen-hint">
              No projects in this workspace yet. Use Dashboard to create one, or choose “Create new project”.
            </p>
          ) : (
            <select
              id="tg-target-project"
              className="tg-select"
              value={targetProjectId}
              onChange={(e) => setTargetProjectId(e.target.value)}
              disabled={actionLoading || submitting}
            >
              {organizationProjects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>
      ) : null}
    </div>
  );

  const approveButtonLabel =
    syncMode === "existing"
      ? actionLoading
        ? "Adding tasks…"
        : `Add ${plan?.task_count ?? ""} tasks to project`
      : actionLoading
        ? "Creating project…"
        : "Create project & tasks";

  const progressSteps = [
    { key: "analyze", label: "Analyzing your description", done: genStatus !== "DRAFT" },
    {
      key: "plan",
      label: "Building sprint plan (AI)",
      done: !GENERATING_STATUSES.has(genStatus) && genStatus !== "DRAFT",
      active: GENERATING_STATUSES.has(genStatus),
    },
    {
      key: "validate",
      label: "Checking plan completeness (AI)",
      done: genStatus === "PENDING_APPROVAL" || genStatus === "SYNCED",
      active: genStatus === "GENERATING",
    },
    {
      key: "ready",
      label: "Preparing review",
      done: genStatus === "PENDING_APPROVAL" || genStatus === "SYNCED",
    },
  ];

  const toggleMember = (userId) => {
    setSelectedMemberIds((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  };

  const handleJobRoleChange = async (member, jobRoleId) => {
    const parsed = jobRoleId ? Number(jobRoleId) : null;
    setJobRoleByMemberId((prev) => ({ ...prev, [member.id]: parsed }));
    if (!orgId) return;
    try {
      await updateMemberJobRole(orgId, member.id, parsed);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save job role.");
    }
  };

  return (
    <div className="dashboard-shell dashboard-shell--viewport">
      <AppSidebar />

      <main className="ai-main tg-main">
        <header className="ai-topbar">
          <h2 className="ai-heading">Generate project plan</h2>
          <div className="ai-topbar-actions">
            <select
              className="ai-select ai-select--compact"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              disabled={projectsLoading || phase !== "form"}
              aria-label="Project"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </header>

        {error ? (
          <div className="ai-error" role="alert">
            {error}
            <button type="button" className="ai-error-dismiss" onClick={() => setError("")}>
              ✕
            </button>
          </div>
        ) : null}

        <div className="tg-scroll">
          {phase === "form" ? (
            <form className="tg-card" onSubmit={handleGenerate}>
              <h3>Describe your project</h3>

              <label className="tg-label" htmlFor="tg-description">
                Project description
              </label>
              <textarea
                id="tg-description"
                className="tg-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe goals, stack, and main features — e.g. ecommerce with payments, admin dashboard, mobile app…"
                maxLength={8000}
                required
              />

              <div className="tg-row" style={{ marginTop: 16 }}>
                <div>
                  <label className="tg-label" htmlFor="tg-sprints">
                    Number of sprints
                  </label>
                  <select
                    id="tg-sprints"
                    className="tg-select"
                    value={sprintCount}
                    onChange={(e) => setSprintCount(e.target.value)}
                  >
                    {[1, 2, 3, 4, 5, 6].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {syncTargetPanel}

              <label className="tg-label" style={{ marginTop: 8 }}>
                Team members (for assignment)
              </label>
              <div className="tg-members">
                {members.length === 0 ? (
                  <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                    {orgId ? "No members in this workspace." : "Select a workspace."}
                  </span>
                ) : (
                  members.map((m) => (
                    <div key={m.id} className="tg-member-row">
                      <label className="tg-member">
                        <input
                          type="checkbox"
                          checked={selectedMemberIds.has(m.user)}
                          onChange={() => toggleMember(m.user)}
                        />
                        <strong>{m.user_email}</strong>
                        <span className="tg-access-role">{m.role_name}</span>
                      </label>
                      <select
                        className="tg-select tg-select--compact"
                        value={jobRoleByMemberId[m.id] ?? ""}
                        onChange={(e) => handleJobRoleChange(m, e.target.value || null)}
                        aria-label={`Job role for ${m.user_email}`}
                      >
                        <option value="">Job role…</option>
                        {jobRoles.map((jr) => (
                          <option key={jr.id} value={jr.id}>
                            {jr.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))
                )}
              </div>

              <div className="tg-form-actions">
                <button
                  type="submit"
                  className="dashboard-button dashboard-button--primary tg-form-submit"
                  disabled={submitting || !orgId || !description.trim() || groqConfigured === false}
                >
                  {submitting ? "Starting…" : "Generate plan"}
                </button>
              </div>
            </form>
          ) : null}

          {phase === "generating" ? (
            <div className="tg-card">
              <h3>Generating your project plan…</h3>
              <p className="tg-muted">
                This may take 30–90 seconds (2 AI calls). Keep this tab open.
              </p>
              <ul className="tg-progress-list">
                {progressSteps.map((step) => (
                  <li
                    key={step.key}
                    className={
                      step.done ? "done" : step.active ? "active" : undefined
                    }
                  >
                    {step.done ? "✅" : step.active ? "🔄" : "⏳"} {step.label}
                  </li>
                ))}
              </ul>
              <p className="tg-muted--sm">Status: {genStatus}</p>
            </div>
          ) : null}

          {phase === "review" && plan ? (
            <>
              <div
                className={`tg-coverage${missingThemes.length > 0 ? " warn" : ""}`}
              >
                <strong>{plan.ai_raw_output?.project_name || "Project plan"}</strong>
                {plan.task_count ? (
                  <span>
                    · {plan.task_count} tasks
                    {plan.sprint_count || plan.ai_raw_output?.sprint_count
                      ? ` · ${plan.sprint_count || plan.ai_raw_output?.sprint_count} sprints`
                      : ""}
                  </span>
                ) : null}
              </div>

              {warnings.length > 0 ? (
                <ul className="tg-warnings">
                  {warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              ) : null}

              {sprintGroups.map(([sprintNum, tasks]) => (
                <section key={sprintNum} className="tg-sprint">
                  <h4 className="tg-sprint-title">Sprint {sprintNum}</h4>
                  {tasks.map((task) => (
                    <div key={task.id} className="tg-task-row">
                      <strong>{task.title}</strong>
                      <span className="tg-badge">{task.category}</span>
                      <span className="tg-badge">{task.story_points} SP</span>
                      <div className="tg-task-row-actions">
                        <button
                          type="button"
                          className="tg-btn tg-btn--ghost tg-btn--sm"
                          onClick={() => setPreviewTask(task)}
                        >
                          Preview
                        </button>
                        <button
                          type="button"
                          className="tg-btn tg-btn--ghost tg-btn--sm"
                          onClick={() => setEditTask({ ...task })}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="tg-btn tg-btn--ghost tg-btn--sm"
                          disabled={actionLoading}
                          onClick={() => handleRegenerateTask(task)}
                        >
                          Regenerate
                        </button>
                      </div>
                    </div>
                  ))}
                </section>
              ))}

              <footer className="tg-footer">
                <p className="tg-footer-intro">
                  <strong>Happy with this plan?</strong>
                  {syncMode === "existing" && selectedProjectName
                    ? ` Tasks will be added to “${selectedProjectName}”.`
                    : " A new project and tasks will be created in your workspace."}
                  {" "}You can change the target below before approving.
                </p>
                {syncTargetPanel}
                <div className="tg-footer-actions">
                  <button
                    type="button"
                    className="tg-btn tg-btn--primary"
                    disabled={actionLoading || genStatus !== "PENDING_APPROVAL"}
                    onClick={handleApprove}
                  >
                    {approveButtonLabel}
                  </button>
                  <button
                    type="button"
                    className="tg-btn tg-btn--danger-outline"
                    disabled={actionLoading}
                    onClick={handleReject}
                  >
                    Discard plan
                  </button>
                </div>
                <div className="tg-regen-panel">
                  <label htmlFor="tg-regen-hint">
                    Optional note for single-task Regenerate
                  </label>
                  <input
                    id="tg-regen-hint"
                    className="tg-input"
                    placeholder="e.g. Add more API detail, split into smaller subtasks…"
                    value={regenHint}
                    onChange={(e) => setRegenHint(e.target.value)}
                  />
                  <p className="tg-regen-hint">
                    Used only when you click <strong>Regenerate</strong> on a task above — not for the
                    whole plan.
                  </p>
                </div>
              </footer>
            </>
          ) : null}

          {phase === "synced" ? (
            <div className="tg-card tg-success">
              <h3>Plan synced successfully</h3>
              <p>
                {syncResult?.created_new_project === false ? (
                  <>
                    Added {syncResult?.tasks_created ?? plan?.task_count ?? 0} tasks to &quot;
                    {syncResult?.project_name || selectedProjectName || "project"}&quot;.
                  </>
                ) : (
                  <>
                    Created project &quot;
                    {syncResult?.project_name || plan?.ai_raw_output?.project_name || "Project"}&quot; with{" "}
                    {syncResult?.tasks_created ?? plan?.task_count ?? 0} tasks.
                  </>
                )}
              </p>
              {syncResult?.project_id ? (
                <p className="tg-muted">Project ID: {syncResult.project_id}</p>
              ) : null}
              <div className="tg-success-actions">
                <Link to="/dashboard" className="tg-btn tg-btn--primary">
                  View dashboard
                </Link>
                <button
                  type="button"
                  className="tg-btn tg-btn--ghost"
                  onClick={() => {
                    setPhase("form");
                    setPlanId(null);
                    setPlan(null);
                    setSyncResult(null);
                  }}
                >
                  Generate another
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {previewTask ? (
          <div className="tg-modal-backdrop" role="dialog" aria-modal="true">
            <div className="tg-modal">
              <div className="tg-modal-header">
                <strong>{previewTask.title}</strong>
                <button
                  type="button"
                  className="ai-error-dismiss"
                  onClick={() => setPreviewTask(null)}
                >
                  ✕
                </button>
              </div>
              <div className="tg-modal-body">
                <div className="tg-preview-meta">
                  {previewTask.category ? (
                    <span className="tg-badge">{previewTask.category}</span>
                  ) : null}
                  {previewTask.story_points ? (
                    <span className="tg-badge">{previewTask.story_points} SP</span>
                  ) : null}
                  {previewTask.suggested_assignee_role ? (
                    <span className="tg-badge">{previewTask.suggested_assignee_role}</span>
                  ) : null}
                </div>
                <div className="tg-preview-content">
                  {previewTask.rendered_body ? (
                    <TaskDescriptionMarkdown text={previewTask.rendered_body} />
                  ) : (
                    <p className="tg-muted">No preview body.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {editTask ? (
          <div className="tg-modal-backdrop" role="dialog" aria-modal="true">
            <div className="tg-modal">
              <div className="tg-modal-header">
                <strong>Edit task</strong>
                <button
                  type="button"
                  className="ai-error-dismiss"
                  onClick={() => setEditTask(null)}
                >
                  ✕
                </button>
              </div>
              <div className="tg-modal-body">
                <label className="tg-label">Title</label>
                <input
                  className="tg-input"
                  value={editTask.title}
                  onChange={(e) => setEditTask({ ...editTask, title: e.target.value })}
                />
                <label className="tg-label" style={{ marginTop: 12 }}>
                  Goal
                </label>
                <input
                  className="tg-input"
                  value={editTask.goal}
                  onChange={(e) => setEditTask({ ...editTask, goal: e.target.value })}
                />
                <label className="tg-label" style={{ marginTop: 12 }}>
                  Description
                </label>
                <textarea
                  className="tg-textarea"
                  style={{ minHeight: 80 }}
                  value={editTask.description}
                  onChange={(e) =>
                    setEditTask({ ...editTask, description: e.target.value })
                  }
                />
                <label className="tg-label" style={{ marginTop: 12 }}>
                  Story points
                </label>
                <select
                  className="tg-select"
                  value={editTask.story_points}
                  onChange={(e) =>
                    setEditTask({ ...editTask, story_points: Number(e.target.value) })
                  }
                >
                  {[1, 2, 3, 5, 8, 13].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
              <div className="tg-modal-footer">
                <button
                  type="button"
                  className="tg-btn tg-btn--ghost"
                  onClick={() => setEditTask(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="dashboard-button dashboard-button--primary"
                  disabled={actionLoading}
                  onClick={handleSaveEdit}
                >
                  {actionLoading ? "Saving…" : "Save changes"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default TaskGenerator;

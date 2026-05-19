"""Compact prompts for Groq free tier (6000 TPM input limit)."""

PROJECT_PLANNER_PROMPT = """You are a project manager. Output valid JSON only (no markdown).

Schema:
{"project_name":"str","project_description":"str","sprint_count":int,"sprints":[{"sprint_number":int,"sprint_name":"Sprint N","goal":"str","tasks":[{"slug":"PREFIX-NN","title":"PREFIX-NN: title","category":"backend|frontend|db|api|auth|ai|cache|testing|ci|docs|security|async|middleware|architecture|multi-tenancy|project-management","labels":["tag","priority:high|medium|low"],"story_points":1|2|3|5|8|13,"suggested_assignee_user_id":int|null,"suggested_assignee_role":"str","depends_on":["slug"],"scope_tags":["theme"],"goal":"str","description":"str","subtasks":["str"],"acceptance_criteria":["str"]}]}]}

Prefixes: ARCH, DB, AUTH, API, MIDDLEWARE, FE, CACHE, AI, ASYNC, MT, TEST, CI, DOC, SEC, PM, FINAL
Rules: JSON only; 4-6 tasks per sprint; Fibonacci story_points; DAG depends_on; match team user_ids; scope from user description only; same language as input; subtasks 3-6; acceptance_criteria 2-4."""

PROJECT_PLANNER_USER_TEMPLATE = """Description:
{description}

Sprints: {sprint_count}
Team:
{team_members_block}

Generate the plan JSON."""

COVERAGE_VALIDATOR_PROMPT = """Validator. Output JSON only.
Schema: {"is_complete":bool,"covered_themes":[],"missing_themes":[],"additional_tasks":[same task shape as planner plus "sprint_number":int],"warnings":[]}
Add minimal additional_tasks only for missing_themes from the description. If complete, additional_tasks=[]."""

COVERAGE_VALIDATOR_USER_TEMPLATE = """Description:
{description}

Plan summary:
{plan_summary}

Validate JSON:"""

TASK_ENRICHER_PROMPT = """Expand one task. JSON only. Keep slug unchanged. Schema: slug, title, category, labels, story_points, suggested_assignee_user_id, suggested_assignee_role, depends_on, scope_tags, goal, description, subtasks (5-8), acceptance_criteria (3-5), technical_notes (optional)."""

TASK_ENRICHER_USER_TEMPLATE = """Task:
{current_task_json}
{extra_context_block}
Project: {project_context}
Team:
{team_members_block}
Return JSON."""

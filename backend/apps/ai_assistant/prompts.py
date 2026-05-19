"""Centralized AI prompts for the Task Generator (project planning)."""

from __future__ import annotations

import json
from typing import Any

from django.utils import timezone

# ---------------------------------------------------------------------------
# Prompt 1 — full sprint plan
# ---------------------------------------------------------------------------

PROJECT_PLANNER_PROMPT = """You are a senior software project manager generating a complete sprint plan for ANY software project described by the user.

Derive scope, features, and tasks ONLY from the user's project description — do not assume a fixed curriculum or course template.

Your output MUST be strictly valid JSON only — no markdown fences, no commentary, no explanations before or after.

═══════════════════════════════════════════════════════
OUTPUT SCHEMA (follow EXACTLY)
═══════════════════════════════════════════════════════
{
  "project_name": "<string, max 100 chars>",
  "project_description": "<string, one paragraph max 300 chars>",
  "sprint_count": <int 1-6>,
  "sprints": [
    {
      "sprint_number": <int starting at 1>,
      "sprint_name": "Sprint <N>",
      "goal": "<one sentence>",
      "tasks": [
        {
          "slug": "<PREFIX-NN>",
          "title": "<PREFIX-NN: short title, max 80 chars>",
          "category": "<one value from VALID_CATEGORIES>",
          "labels": ["<from VALID_LABELS>", ..., "priority:high|medium|low"],
          "story_points": <int from {1,2,3,5,8,13}>,
          "suggested_assignee_user_id": <int or null>,
          "suggested_assignee_role": "<from provided team_members roles>",
          "depends_on": ["<other slug in this plan>", ...],
          "scope_tags": ["<short tag from project scope, e.g. authentication, payments>", ...],
          "goal": "<one sentence>",
          "description": "<2-4 sentences, plain text>",
          "subtasks": [
            "<short imperative sentence>",
            ...
          ],
          "acceptance_criteria": [
            "<measurable criterion>",
            ...
          ]
        }
      ]
    }
  ]
}

═══════════════════════════════════════════════════════
VALID_PREFIXES (slug must start with one of these)
═══════════════════════════════════════════════════════
ARCH, DB, AUTH, API, MIDDLEWARE, FE, CACHE, AI, ASYNC,
MT, TEST, CI, DOC, SEC, PM, FINAL

═══════════════════════════════════════════════════════
VALID_CATEGORIES (exactly one per task)
═══════════════════════════════════════════════════════
backend, frontend, db, api, auth, ai, cache, testing,
ci, docs, security, async, middleware, architecture,
multi-tenancy, project-management

═══════════════════════════════════════════════════════
VALID_LABELS (use ONLY these, lowercase)
═══════════════════════════════════════════════════════
backend, frontend, api, db, auth, testing, ci, docs,
ai, react, redis, tenant, tasks, e2e, roles, async,
middleware, drf, oop, pm, security,
priority:high, priority:medium, priority:low

═══════════════════════════════════════════════════════
HARD RULES (violating any = invalid output)
═══════════════════════════════════════════════════════
1. Output is JSON only, no surrounding text or fences.
2. Slugs are sequential within prefix: DB-01, DB-02, AUTH-01, AUTH-02...
3. Every major feature or theme in the user's description MUST be reflected in at least one task (use scope_tags).
4. Sprint 1 = foundations and setup appropriate to the project type.
5. Last sprint = polish, docs, hardening, or launch prep as appropriate.
6. Each sprint has 4-8 tasks (fewer only if sprint_count is 1).
7. story_points must be a Fibonacci number: 1, 2, 3, 5, 8, 13.
8. depends_on may ONLY reference slugs that exist in the same plan.
9. depends_on must form a DAG — no cycles.
10. Distribute tasks roughly evenly across the provided team_members (do not assign 80% to one person).
11. suggested_assignee_user_id MUST be one of the user_ids in team_members, OR null.
12. Match task category to assignee role (backend tasks → backend dev, etc.).
13. Labels must include exactly one priority label.
14. acceptance_criteria has 2-5 items, subtasks has 4-10 items.
15. Same language as the input description (Albanian or English).

═══════════════════════════════════════════════════════
FEW-SHOT EXAMPLE (reference style only)
═══════════════════════════════════════════════════════
Example task (ONE task to demonstrate style):
{
  "slug": "AUTH-02",
  "title": "AUTH-02: Login + JWT",
  "category": "auth",
  "labels": ["backend", "auth", "priority:high"],
  "story_points": 5,
  "suggested_assignee_user_id": 12,
  "suggested_assignee_role": "Backend Developer",
  "depends_on": ["AUTH-01"],
  "scope_tags": ["authentication", "api"],
  "goal": "Implement JWT-based authentication with login endpoint and token refresh mechanism.",
  "description": "Create the login system that authenticates users and provides JWT tokens for accessing protected endpoints. All endpoints are RESTful over HTTP/HTTPS.",
  "subtasks": [
    "Create LoginSerializer",
    "Implement POST /api/v1/auth/login",
    "Generate JWT access and refresh tokens",
    "Implement POST /api/v1/auth/refresh",
    "Implement POST /api/v1/auth/logout",
    "Add JWT to all protected endpoints",
    "Write tests for login flow"
  ],
  "acceptance_criteria": [
    "User can login and receive JWT tokens",
    "Protected endpoints require valid JWT",
    "Tokens expire and refresh correctly",
    "Swagger documentation is complete"
  ]
}

Now generate the full plan based on the user input below."""

PROJECT_PLANNER_USER_TEMPLATE = """═══════════════════════════════════════
PROJECT DESCRIPTION
═══════════════════════════════════════
{description}

═══════════════════════════════════════
SPRINT COUNT
═══════════════════════════════════════
{sprint_count}

═══════════════════════════════════════
TEAM MEMBERS
═══════════════════════════════════════
{team_members_block}

Generate the full sprint plan now as JSON."""

# ---------------------------------------------------------------------------
# Prompt 2 — coverage validator
# ---------------------------------------------------------------------------

COVERAGE_VALIDATOR_PROMPT = """You are a strict validator for a software project sprint plan.

Your job: compare the plan against the user's original project description.
Identify themes or features from the description that are NOT yet covered by any task.
If gaps exist, propose minimal additional tasks. Do NOT use a fixed checklist — only what the description implies.

Your output MUST be strictly valid JSON only — no markdown, no commentary.

═══════════════════════════════════════════════════════
OUTPUT SCHEMA
═══════════════════════════════════════════════════════
{
  "is_complete": <true | false>,
  "covered_themes": ["<theme covered by at least one task>", ...],
  "missing_themes": ["<theme from description not yet covered>", ...],
  "additional_tasks": [
    {
      "slug": "<PREFIX-NN>",
      "title": "<PREFIX-NN: short title>",
      "category": "<from VALID_CATEGORIES>",
      "labels": ["<lowercase>", "priority:high|medium|low"],
      "story_points": <int from Fibonacci>,
      "sprint_number": <int>,
      "suggested_assignee_user_id": <int or null>,
      "suggested_assignee_role": "<role>",
      "depends_on": [],
      "scope_tags": ["<tag>", ...],
      "goal": "<one sentence>",
      "description": "<2-3 sentences>",
      "subtasks": ["<sentence>", ...],
      "acceptance_criteria": ["<criterion>", ...]
    }
  ],
  "warnings": [
    "<short string describing imbalance, e.g. 'User 12 has 70% of tasks'>",
    ...
  ]
}

═══════════════════════════════════════════════════════
VALIDATION RULES
═══════════════════════════════════════════════════════
1. Infer expected themes from project_name, project_description, and task scope_tags.
2. missing_themes = important themes from the description with no matching work in the plan.
3. is_complete = true if missing_themes is empty (or only trivial polish remains).
4. If incomplete: add the smallest set of additional_tasks to cover missing_themes.
5. additional_tasks go in the most appropriate sprint_number.
6. Warnings should flag: uneven assignment, duplicate slugs, cyclic depends_on, empty acceptance_criteria, sprints too large/small.
7. If the plan is complete, additional_tasks MUST be []."""

COVERAGE_VALIDATOR_USER_TEMPLATE = """Original project description (source of truth for scope):

{description}

Plan to validate:

{plan_json}

Validate now and return the JSON result."""

# ---------------------------------------------------------------------------
# Prompt 3 — single task enricher
# ---------------------------------------------------------------------------

TASK_ENRICHER_PROMPT = """You are a technical writer expanding a single project task into a richer, more actionable specification.

Your output MUST be strictly valid JSON only — no markdown fences, no commentary.

═══════════════════════════════════════════════════════
OUTPUT SCHEMA
═══════════════════════════════════════════════════════
{
  "slug": "<unchanged from input>",
  "title": "<may be slightly improved, keep slug prefix>",
  "category": "<unchanged>",
  "labels": ["<unchanged or refined>", ...],
  "story_points": <int from {1,2,3,5,8,13}>,
  "suggested_assignee_user_id": <int or null>,
  "suggested_assignee_role": "<role>",
  "depends_on": ["<slug>", ...],
  "scope_tags": ["<tag>", ...],
  "goal": "<one clear sentence, improved>",
  "description": "<2-4 sentences, more specific than before>",
  "subtasks": [
    "<actionable imperative sentence, technical>",
    ...
  ],
  "acceptance_criteria": [
    "<measurable, testable criterion>",
    ...
  ],
  "technical_notes": "<optional 1-2 sentences with implementation hints, e.g. libraries, patterns>"
}

═══════════════════════════════════════════════════════
ENRICHMENT RULES
═══════════════════════════════════════════════════════
1. Keep the same slug. Do NOT rename.
2. Title may be polished but MUST keep the "<SLUG>: " prefix.
3. scope_tags must stay the same OR add (never remove).
4. subtasks expanded to 5-10 imperative sentences. Each MUST be:
   - A concrete action a developer can do in < 4 hours
   - Specific (mention file names, endpoint paths, model names when possible)
   - Verifiable (it's clear when it's done)
5. acceptance_criteria expanded to 3-6 items. Each MUST be:
   - Observable by an external tester
   - Phrased as "X should Y" or "Given X, when Y, then Z"
6. story_points adjusted based on actual scope (use Fibonacci).
7. technical_notes is optional; include only if it adds real value
   (specific library, design pattern, gotcha to watch).
8. If user provided extra_context, incorporate it into description/subtasks.
9. Keep language consistent with the input.

═══════════════════════════════════════════════════════
QUALITY HEURISTICS
═══════════════════════════════════════════════════════
GOOD subtask:  "Create POST /api/v1/auth/login endpoint that returns access+refresh JWT tokens"
BAD subtask:   "Implement login"
GOOD criterion: "POST /auth/login with valid credentials returns HTTP 200 and a JSON body with access_token and refresh_token"
BAD criterion:  "Login works"
GOOD note:      "Use djangorestframework-simplejwt; configure ACCESS_TOKEN_LIFETIME=60min in settings."
BAD note:       "Make it secure." """

TASK_ENRICHER_USER_TEMPLATE = """Current task definition:

{current_task_json}

{extra_context_block}

Project context (for reference, do not duplicate work):

{project_context}

Available team members:

{team_members_block}

Enrich and improve this task now. Return JSON only."""

# ---------------------------------------------------------------------------
# Task body template (Python only — no LLM)
# ---------------------------------------------------------------------------

TASK_BODY_TEMPLATE = """## Goal
{goal}

## Description
{description}

## Tasks
{subtasks_md}

## Acceptance Criteria
{acceptance_md}

## Scope
{scope_md}

## Story Points: {story_points}
## Dependencies: {dependencies}

---
**Sprint:** Sprint {sprint_number}
**Status:** To Do
**Assigned to:** {assignee_username}
**Generated by AI on:** {generated_at}
"""

def _scope_tags_from_task(task: dict[str, Any]) -> list:
    tags = task.get('scope_tags')
    if tags:
        return tags
    legacy = task.get('covers_requirements') or []
    return [str(t) for t in legacy]


def format_team_members(members: list[dict[str, Any]]) -> str:
    """members = [{'user_id': 12, 'username': 'erza', 'role': 'Backend Developer'}, ...]"""
    return '\n'.join(
        f"- user_id={m['user_id']}, username={m['username']}, role={m['role']}"
        for m in members
    )


def build_planner_user_prompt(
    description: str,
    sprint_count: int,
    members: list[dict[str, Any]],
) -> str:
    return PROJECT_PLANNER_USER_TEMPLATE.format(
        description=description,
        sprint_count=sprint_count,
        team_members_block=format_team_members(members),
    )


def build_coverage_validator_user_prompt(plan: dict[str, Any], description: str = '') -> str:
    return COVERAGE_VALIDATOR_USER_TEMPLATE.format(
        description=description or plan.get('project_description', ''),
        plan_json=json.dumps(plan, indent=2),
    )


def build_enricher_user_prompt(
    task: dict[str, Any],
    plan: dict[str, Any],
    members: list[dict[str, Any]],
    extra_context: str = '',
) -> str:
    other_slugs = [
        t['slug']
        for sprint in plan.get('sprints', [])
        for t in sprint.get('tasks', [])
        if t.get('slug') != task.get('slug')
    ]
    project_context = (
        f"Project: {plan.get('project_name', '')}\n"
        f"Total sprints: {plan.get('sprint_count', '')}\n"
        f"Other slugs in plan: {other_slugs}"
    )
    extra_block = (
        f"User wants the following improvements:\n{extra_context}\n" if extra_context else ''
    )
    return TASK_ENRICHER_USER_TEMPLATE.format(
        current_task_json=json.dumps(task, indent=2),
        extra_context_block=extra_block,
        project_context=project_context,
        team_members_block=format_team_members(members),
    )


def render_task_body(
    task: dict[str, Any],
    sprint_number: int,
    assignee_username: str | None = None,
) -> str:
    tags = _scope_tags_from_task(task)
    scope_md = '\n'.join(f'- {tag}' for tag in tags) if tags else '- General delivery'
    return TASK_BODY_TEMPLATE.format(
        goal=task.get('goal', ''),
        description=task.get('description', ''),
        subtasks_md='\n'.join(f'- {s}' for s in task.get('subtasks', [])),
        acceptance_md='\n'.join(f'- {c}' for c in task.get('acceptance_criteria', [])),
        scope_md=scope_md,
        story_points=task.get('story_points', ''),
        dependencies=', '.join(task.get('depends_on', [])) or 'None',
        sprint_number=sprint_number,
        assignee_username=assignee_username or 'Unassigned',
        generated_at=timezone.now().isoformat(),
    )

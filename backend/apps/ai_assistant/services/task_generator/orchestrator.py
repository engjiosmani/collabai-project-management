from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.ai_assistant.models import PlannedTask, ProjectPlanDraft
from apps.ai_assistant.prompts import _scope_tags_from_task, format_team_members, render_task_body
from apps.ai_assistant.prompts_compact import (
    COVERAGE_VALIDATOR_PROMPT,
    COVERAGE_VALIDATOR_USER_TEMPLATE,
    PROJECT_PLANNER_PROMPT,
    PROJECT_PLANNER_USER_TEMPLATE,
    TASK_ENRICHER_PROMPT,
    TASK_ENRICHER_USER_TEMPLATE,
)
from apps.ai_assistant.services.groq_client import GroqClient
from apps.ai_assistant.services.task_generator.json_utils import (
    ensure_task_slug,
    normalize_plan,
    parse_llm_json,
)
from apps.workspaces.services.job_role_assignment import apply_job_role_assignments

logger = logging.getLogger(__name__)


def _format_groq_error(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        field = exc.args[0] if exc.args else 'field'
        return f'AI response was missing "{field}". Please try generating again.'
    message = str(exc)
    if '413' in message or 'Request too large' in message or 'tokens per minute' in message:
        return (
            'Groq request is too large for the free tier (6000 token limit). '
            'Try fewer sprints, a shorter description, or upgrade Groq billing.'
        )
    if '401' in message or 'invalid_api_key' in message.lower():
        return 'Invalid GROQ_API_KEY. Create a new key at console.groq.com and update backend/.env.'
    return message[:500]


def _plan_summary(plan: dict[str, Any]) -> str:
    lines = [f"Project: {plan.get('project_name', '')}"]
    for sprint in plan.get('sprints', []):
        for task in sprint.get('tasks', []):
            tags = ', '.join(task.get('scope_tags') or [])
            lines.append(f"- {task.get('slug')}: {tags}")
    return '\n'.join(lines)


def build_planner_user_prompt(description: str, sprint_count: int, members: list[dict]) -> str:
    return PROJECT_PLANNER_USER_TEMPLATE.format(
        description=description[:4000],
        sprint_count=sprint_count,
        team_members_block=format_team_members(members),
    )


def build_coverage_validator_user_prompt(plan: dict[str, Any], description: str = '') -> str:
    return COVERAGE_VALIDATOR_USER_TEMPLATE.format(
        description=(description or plan.get('project_description', ''))[:2000],
        plan_summary=_plan_summary(plan),
    )


def build_enricher_user_prompt(
    task: dict[str, Any],
    plan: dict[str, Any],
    members: list[dict],
    extra_context: str = '',
) -> str:
    extra_block = f"Notes: {extra_context}\n" if extra_context else ''
    return TASK_ENRICHER_USER_TEMPLATE.format(
        current_task_json=json.dumps(task, ensure_ascii=False)[:3000],
        extra_context_block=extra_block,
        project_context=plan.get('project_name', ''),
        team_members_block=format_team_members(members),
    )


class TaskGeneratorService:
    """Runs Prompt 1 → Prompt 2 pipeline and persists PlannedTask rows."""

    def __init__(self, llm: GroqClient | None = None):
        self.llm = llm or GroqClient()

    def _call_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        raw = self.llm.chat(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
        return parse_llm_json(raw)

    def generate_project_plan(
        self,
        *,
        description: str,
        sprint_count: int,
        team_members: list[dict[str, Any]],
    ) -> dict[str, Any]:
        plan = self._call_json(
            system=PROJECT_PLANNER_PROMPT,
            user=build_planner_user_prompt(description, sprint_count, team_members),
            temperature=0.3,
            max_tokens=3500,
        )

        validation = self._call_json(
            system=COVERAGE_VALIDATOR_PROMPT,
            user=build_coverage_validator_user_prompt(plan, description),
            temperature=0.1,
            max_tokens=1200,
        )

        if not validation.get('is_complete'):
            for task in validation.get('additional_tasks', []):
                sprint_number = task.pop('sprint_number', 1)
                sprint = next(
                    (s for s in plan.get('sprints', []) if s.get('sprint_number') == sprint_number),
                    None,
                )
                if sprint is None and plan.get('sprints'):
                    sprint = plan['sprints'][-1]
                if sprint is not None:
                    sprint.setdefault('tasks', []).append(task)

        plan['validation'] = {
            'covered_themes': validation.get('covered_themes', []),
            'missing_themes': validation.get('missing_themes', []),
            'warnings': validation.get('warnings', []),
            'is_complete': validation.get('is_complete', False),
        }
        normalize_plan(plan)
        plan = apply_job_role_assignments(plan, team_members)
        return plan

    def regenerate_single_task(
        self,
        *,
        plan: dict[str, Any],
        slug: str,
        team_members: list[dict[str, Any]],
        hint: str = '',
    ) -> dict[str, Any]:
        task = next(
            t
            for sprint in plan.get('sprints', [])
            for t in sprint.get('tasks', [])
            if t.get('slug') == slug
        )
        enriched = self._call_json(
            system=TASK_ENRICHER_PROMPT,
            user=build_enricher_user_prompt(task, plan, team_members, hint),
            temperature=0.4,
            max_tokens=2048,
        )
        enriched.setdefault('slug', task.get('slug') or slug)
        for sprint in plan.get('sprints', []):
            for index, item in enumerate(sprint.get('tasks', [])):
                if item.get('slug') == slug:
                    sprint['tasks'][index] = enriched
                    return enriched
        raise ValueError(f'Task slug {slug} not found in plan.')

    @transaction.atomic
    def persist_plan(self, draft: ProjectPlanDraft, plan: dict[str, Any]) -> ProjectPlanDraft:
        draft.ai_raw_output = plan
        draft.validation_meta = plan.get('validation', {})
        draft.save(update_fields=['ai_raw_output', 'validation_meta', 'updated_at'])

        PlannedTask.objects.filter(plan=draft).delete()
        User = get_user_model()
        order = 0
        for sprint in plan.get('sprints', []):
            sprint_number = sprint.get('sprint_number', 1)
            for task in sprint.get('tasks', []):
                order += 1
                user_id = task.get('suggested_assignee_user_id')
                assignee = User.objects.filter(pk=user_id).first() if user_id else None
                username = assignee.username if assignee else None
                slug = task.get('slug') or ensure_task_slug(
                    task, sprint_number=sprint_number, index=order
                )
                body = render_task_body(task, sprint_number, username)
                PlannedTask.objects.create(
                    plan=draft,
                    slug=slug,
                    title=task.get('title', slug),
                    category=task.get('category', ''),
                    sprint_number=sprint_number,
                    story_points=task.get('story_points', 3),
                    labels=task.get('labels', []),
                    suggested_assignee=assignee,
                    suggested_assignee_role=task.get('suggested_assignee_role', ''),
                    depends_on=task.get('depends_on', []),
                    covers_requirements=_scope_tags_from_task(task),
                    goal=task.get('goal', ''),
                    description=task.get('description', ''),
                    subtasks=task.get('subtasks', []),
                    acceptance_criteria=task.get('acceptance_criteria', []),
                    technical_notes=task.get('technical_notes', ''),
                    rendered_body=body,
                    order=order,
                )

        return draft

    def update_single_planned_task(
        self,
        planned: PlannedTask,
        task: dict[str, Any],
        sprint_number: int,
    ) -> PlannedTask:
        User = get_user_model()
        user_id = task.get('suggested_assignee_user_id')
        assignee = User.objects.filter(pk=user_id).first() if user_id else None
        username = assignee.username if assignee else None

        planned.title = task.get('title', planned.slug)
        planned.category = task.get('category', '')
        planned.story_points = task.get('story_points', planned.story_points)
        planned.labels = task.get('labels', [])
        planned.suggested_assignee = assignee
        planned.suggested_assignee_role = task.get('suggested_assignee_role', '')
        planned.depends_on = task.get('depends_on', [])
        planned.covers_requirements = _scope_tags_from_task(task)
        planned.goal = task.get('goal', '')
        planned.description = task.get('description', '')
        planned.subtasks = task.get('subtasks', [])
        planned.acceptance_criteria = task.get('acceptance_criteria', [])
        planned.technical_notes = task.get('technical_notes', '')
        planned.rendered_body = render_task_body(task, sprint_number, username)
        planned.is_edited = True
        planned.save()
        return planned

    def run_generation(self, draft_id: int) -> None:
        draft = ProjectPlanDraft.objects.select_related('organization').get(pk=draft_id)
        draft.status = ProjectPlanDraft.Status.GENERATING
        draft.error_message = ''
        draft.save(update_fields=['status', 'error_message', 'updated_at'])

        try:
            plan = self.generate_project_plan(
                description=draft.input_description,
                sprint_count=draft.sprint_count,
                team_members=draft.team_members or [],
            )
            self.persist_plan(draft, plan)
            draft.status = ProjectPlanDraft.Status.PENDING_APPROVAL
            draft.save(update_fields=['status', 'updated_at'])
        except Exception as exc:
            logger.exception('Task generator failed for plan %s', draft_id)
            draft.status = ProjectPlanDraft.Status.FAILED
            draft.error_message = _format_groq_error(exc)
            draft.save(update_fields=['status', 'error_message', 'updated_at'])

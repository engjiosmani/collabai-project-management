from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.ai_assistant.models import PlannedTask, ProjectPlanDraft
from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus


class PlanMaterializer:
    """Convert an approved plan into Project + Task records in the database."""

    PRIORITY_MAP = {
        'priority:high': 'High',
        'priority:medium': 'Medium',
        'priority:low': 'Low',
    }

    @transaction.atomic
    def approve(self, draft: ProjectPlanDraft) -> Project:
        if draft.status != ProjectPlanDraft.Status.PENDING_APPROVAL:
            raise ValueError(f'Cannot approve plan in status {draft.status}.')

        plan_data = draft.ai_raw_output or {}
        project_name = plan_data.get('project_name') or 'Generated project'
        project_description = plan_data.get('project_description', '')

        if draft.target_project_id:
            project = draft.target_project
            created_new = False
        else:
            project = self._create_project(
                organization=draft.organization,
                base_name=project_name[:150],
                description=project_description,
            )
            created_new = True

        todo_status, _ = TaskStatus.objects.get_or_create(name='To Do')
        default_priority, _ = TaskPriority.objects.get_or_create(name='Medium', defaults={'level': 2})

        for planned in draft.planned_tasks.select_related('suggested_assignee').order_by('order'):
            priority = self._resolve_priority(planned.labels) or default_priority
            Task.objects.create(
                project=project,
                title=planned.title[:200],
                description=planned.rendered_body or planned.description,
                status=todo_status,
                priority=priority,
                assigned_to=planned.suggested_assignee,
            )

        draft.project = project
        draft.status = ProjectPlanDraft.Status.SYNCED
        draft.approved_at = timezone.now()
        draft.synced_at = timezone.now()
        draft.save(update_fields=['project', 'status', 'approved_at', 'synced_at', 'updated_at'])
        project._created_new_for_plan = created_new  # noqa: SLF001 — API hint for clients
        return project

    def _create_project(self, *, organization, base_name: str, description: str) -> Project:
        """Create a project; if the name exists in the organization, append (2), (3), …"""
        name = (base_name or 'Generated project').strip() or 'Generated project'
        candidate = name[:150]
        suffix = 2
        while Project.objects.filter(organization=organization, name=candidate).exists():
            tail = f' ({suffix})'
            candidate = f'{name[: 150 - len(tail)]}{tail}'
            suffix += 1
            if suffix > 50:
                raise ValueError(
                    f'Could not create a unique project name for "{name}". '
                    'Rename or delete an existing project with the same name.'
                )
        return Project.objects.create(
            organization=organization,
            name=candidate,
            description=description,
            is_active=True,
        )

    def _resolve_priority(self, labels: list) -> TaskPriority | None:
        for label in labels or []:
            name = self.PRIORITY_MAP.get(label)
            if name:
                priority, _ = TaskPriority.objects.get_or_create(
                    name=name,
                    defaults={'level': {'High': 1, 'Medium': 2, 'Low': 3}.get(name, 2)},
                )
                return priority
        return None

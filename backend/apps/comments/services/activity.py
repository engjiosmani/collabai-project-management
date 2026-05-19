"""Create workspace activity log entries for task and comment events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from apps.comments.models import ActivityLog

if TYPE_CHECKING:
    from apps.tasks.models import Task
    from django.contrib.auth.models import AbstractUser


def record_activity(
    *,
    task: Task,
    user: Optional[AbstractUser],
    action: str,
    description: str = '',
) -> ActivityLog:
    return ActivityLog.objects.create(
        task=task,
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        description=(description or '').strip(),
    )


def _status_label(task: Task) -> str:
    return task.status.name if task.status_id and task.status else 'Unassigned'


def _assignee_label(task: Task) -> str:
    if task.assigned_to_id and task.assigned_to:
        return task.assigned_to.email or task.assigned_to.get_username()
    return 'Unassigned'


def log_task_created(*, task: Task, user) -> ActivityLog:
    return record_activity(
        task=task,
        user=user,
        action='Task created',
        description=f'Created task "{task.title}".',
    )


def log_task_deleted(*, task: Task, user) -> ActivityLog:
    return record_activity(
        task=task,
        user=user,
        action='Task deleted',
        description=f'Deleted task "{task.title}".',
    )


def log_task_updated(*, task: Task, user, previous: Task) -> list[ActivityLog]:
    """Emit one or more log rows for meaningful field changes."""
    logs: list[ActivityLog] = []

    if previous.status_id != task.status_id:
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Status changed',
                description=(
                    f'"{task.title}" moved from {_status_label(previous)} to {_status_label(task)}.'
                ),
            )
        )

    if previous.assigned_to_id != task.assigned_to_id:
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Assignee changed',
                description=(
                    f'"{task.title}" reassigned from {_assignee_label(previous)} '
                    f'to {_assignee_label(task)}.'
                ),
            )
        )

    if previous.title != task.title:
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Task renamed',
                description=f'Renamed "{previous.title}" to "{task.title}".',
            )
        )

    if (previous.description or '') != (task.description or ''):
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Description updated',
                description=f'Updated description on "{task.title}".',
            )
        )

    if previous.due_date != task.due_date:
        prev_due = previous.due_date.isoformat() if previous.due_date else 'none'
        new_due = task.due_date.isoformat() if task.due_date else 'none'
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Due date changed',
                description=f'"{task.title}" due date changed from {prev_due} to {new_due}.',
            )
        )

    if previous.priority_id != task.priority_id:
        prev_name = previous.priority.name if previous.priority_id and previous.priority else 'none'
        new_name = task.priority.name if task.priority_id and task.priority else 'none'
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Priority changed',
                description=f'"{task.title}" priority changed from {prev_name} to {new_name}.',
            )
        )

    if previous.project_id != task.project_id:
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Project changed',
                description=f'"{task.title}" moved to another project.',
            )
        )

    if not logs:
        logs.append(
            record_activity(
                task=task,
                user=user,
                action='Task updated',
                description=f'Updated task "{task.title}".',
            )
        )

    return logs


def log_comment_added(*, task: Task, user, content: str) -> ActivityLog:
    preview = (content or '').strip()
    if len(preview) > 120:
        preview = f'{preview[:117]}...'
    return record_activity(
        task=task,
        user=user,
        action='Comment added',
        description=f'Comment on "{task.title}": {preview}' if preview else f'Comment on "{task.title}".',
    )

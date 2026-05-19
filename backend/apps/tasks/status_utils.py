"""Helpers for interpreting task status names (e.g. dashboard "completed" counts)."""

from __future__ import annotations

from apps.tasks.models import TaskStatus

COMPLETED_STATUS_HINTS = (
    'done',
    'completed',
    'complete',
    'closed',
    'resolved',
    'finished',
    'deployed',
)


def is_completed_status_name(name: str | None) -> bool:
    if not name:
        return False
    normalized = name.lower()
    return any(hint in normalized for hint in COMPLETED_STATUS_HINTS)


def completed_task_status_ids() -> list[int]:
    """Status PKs that count as completed (portable across SQLite and Postgres)."""
    return [
        status.pk
        for status in TaskStatus.objects.only('id', 'name')
        if is_completed_status_name(status.name)
    ]

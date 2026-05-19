"""Workload metrics and burnout / rebalance alerts from task history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import mean

from django.utils import timezone

from apps.comments.models import ActivityLog
from apps.tasks.models import Task
from apps.tasks.status_utils import completed_task_status_ids
from apps.organizations.models import OrganizationMember
from apps.workspaces.models import TeamMember


DEFAULT_HOURS_PER_TASK = 2.0
HIGH_PRIORITY_HOURS = 4.0


def _is_high_priority(task: Task) -> bool:
    if not task.priority_id:
        return False
    name = (task.priority.name or '').lower()
    if any(h in name for h in ('high', 'critical', 'urgent')):
        return True
    return (task.priority.level or 0) >= 3


def _estimate_hours(task: Task) -> float:
    base = HIGH_PRIORITY_HOURS if _is_high_priority(task) else DEFAULT_HOURS_PER_TASK
    desc_len = len(task.description or '')
    if desc_len > 500:
        base += 1.0
    elif desc_len > 1500:
        base += 2.0
    return base


@dataclass
class MemberWorkload:
    user_id: int
    email: str
    active_tasks: int
    high_priority_tasks: int
    estimated_hours: float
    avg_completion_hours: float | None
    load_trend: str  # increasing | decreasing | stable
    completed_last_7d: int
    completed_prev_7d: int


def _members_for_organization(organization_id: int):
    members = OrganizationMember.objects.filter(organization_id=organization_id).select_related('user')
    if members.exists():
        return members
    return TeamMember.objects.filter(workspace__organization_id=organization_id).select_related('user')


def compute_member_workloads(organization_id: int) -> list[MemberWorkload]:
    done_ids = completed_task_status_ids()
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    members = _members_for_organization(organization_id)
    results: list[MemberWorkload] = []

    for member in members:
        user = member.user
        if not user:
            continue

        tasks_qs = Task.objects.filter(
            project__organization_id=organization_id,
            assigned_to=user,
        ).select_related('priority', 'status')

        active_qs = tasks_qs.exclude(status_id__in=done_ids) if done_ids else tasks_qs
        active_list = list(active_qs)
        high_pri = sum(1 for t in active_list if _is_high_priority(t))
        est_hours = sum(_estimate_hours(t) for t in active_list)

        completed_logs = ActivityLog.objects.filter(
            task__project__organization_id=organization_id,
            user=user,
            action='Status changed',
            created_at__gte=two_weeks_ago,
        ).select_related('task')

        completion_hours: list[float] = []
        for log in completed_logs[:50]:
            if 'to Done' in (log.description or '') or 'to done' in (log.description or '').lower():
                task = log.task
                if task and task.created_at:
                    delta = log.created_at - task.created_at
                    completion_hours.append(delta.total_seconds() / 3600.0)

        avg_completion = mean(completion_hours) if completion_hours else None

        completed_last = tasks_qs.filter(
            status_id__in=done_ids,
            updated_at__gte=week_ago,
        ).count() if done_ids else 0
        completed_prev = tasks_qs.filter(
            status_id__in=done_ids,
            updated_at__gte=two_weeks_ago,
            updated_at__lt=week_ago,
        ).count() if done_ids else 0

        if completed_last > completed_prev + 1:
            trend = 'increasing'
        elif completed_last < completed_prev - 1:
            trend = 'decreasing'
        else:
            trend = 'stable'

        results.append(
            MemberWorkload(
                user_id=user.pk,
                email=user.email or user.get_username(),
                active_tasks=len(active_list),
                high_priority_tasks=high_pri,
                estimated_hours=round(est_hours, 1),
                avg_completion_hours=round(avg_completion, 1) if avg_completion else None,
                load_trend=trend,
                completed_last_7d=completed_last,
                completed_prev_7d=completed_prev,
            )
        )

    return results


def build_workload_alerts(organization_id: int, workloads: list[MemberWorkload]) -> list[dict]:
    """Return alert dicts ready for TeamPulseAlert.objects.create."""
    alerts: list[dict] = []
    overloaded = [w for w in workloads if w.active_tasks >= 8 or w.high_priority_tasks >= 4]
    underloaded = [
        w
        for w in workloads
        if w.active_tasks <= 3 and w.high_priority_tasks == 0 and w.estimated_hours < 12
    ]

    for w in overloaded:
        if w.high_priority_tasks >= 4 or w.active_tasks >= 10:
            alerts.append(
                {
                    'user_id': w.user_id,
                    'related_user_id': None,
                    'alert_type': 'burnout_risk',
                    'severity': 'warning',
                    'title': f'{w.email.split("@")[0]} may be overloaded',
                    'message': (
                        f'⚠️ {w.email} has {w.active_tasks} active tasks '
                        f'({w.high_priority_tasks} high-priority) — ~{w.estimated_hours}h estimated. '
                        f'Burnout risk; consider redistributing work.'
                    ),
                    'metrics': w.__dict__,
                }
            )

    for under in underloaded:
        alerts.append(
            {
                'user_id': under.user_id,
                'related_user_id': None,
                'alert_type': 'capacity_available',
                'severity': 'suggestion',
                'title': f'{under.email.split("@")[0]} has capacity',
                'message': (
                    f'💡 {under.email} has capacity (~{under.active_tasks} active tasks, '
                    f'~{under.estimated_hours}h estimated) and could take more work.'
                ),
                'metrics': under.__dict__,
            }
        )

    for over in sorted(overloaded, key=lambda x: -x.active_tasks)[:3]:
        for under in sorted(underloaded, key=lambda x: x.active_tasks)[:3]:
            if over.user_id == under.user_id:
                continue
            move_count = min(3, max(1, over.active_tasks // 3))
            alerts.append(
                {
                    'user_id': over.user_id,
                    'related_user_id': under.user_id,
                    'alert_type': 'rebalance_suggestion',
                    'severity': 'suggestion',
                    'title': 'Rebalance suggestion',
                    'message': (
                        f'💡 Move up to {move_count} tasks from {over.email.split("@")[0]} '
                        f'to {under.email.split("@")[0]} to balance workload.'
                    ),
                    'metrics': {
                        'from_user_id': over.user_id,
                        'to_user_id': under.user_id,
                        'suggested_moves': move_count,
                    },
                }
            )
            break
        break

    return alerts

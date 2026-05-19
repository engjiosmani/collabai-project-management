"""Daily standup: DB activity + GitHub commits + optional Groq narrative."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.comments.models import ActivityLog, Comment
from apps.tasks.models import Task
from apps.tasks.status_utils import completed_task_status_ids
from apps.workspaces.models import TeamMember

from ..groq_client import GroqClient
from .github_client import fetch_member_commits

logger = logging.getLogger(__name__)
User = get_user_model()


def _gather_member_context(
    *,
    workspace_id: int,
    user_id: int,
    since,
    github_config,
) -> dict:
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return {}

    tasks_changed = list(
        Task.objects.filter(
            project__workspace_id=workspace_id,
            assigned_to_id=user_id,
            updated_at__gte=since,
        ).values('title', 'status__name', 'updated_at')[:20]
    )

    activity = list(
        ActivityLog.objects.filter(
            task__project__workspace_id=workspace_id,
            user_id=user_id,
            created_at__gte=since,
        )
        .select_related('task')
        .order_by('-created_at')[:15]
        .values('action', 'description', 'created_at')
    )

    comments = list(
        Comment.objects.filter(
            task__project__workspace_id=workspace_id,
            author_id=user_id,
            created_at__gte=since,
        )
        .select_related('task')
        .order_by('-created_at')[:10]
        .values('content', 'task__title', 'created_at')
    )

    commits: list[dict] = []
    if github_config and github_config.is_enabled and github_config.access_token:
        login_map = github_config.member_github_logins or {}
        gh_login = login_map.get(str(user_id)) or login_map.get(user_id)
        if gh_login and github_config.repos:
            commits = fetch_member_commits(
                access_token=github_config.access_token,
                repos=github_config.repos,
                since=since,
                github_login=gh_login,
            )

    open_qs = Task.objects.filter(
        project__workspace_id=workspace_id,
        assigned_to_id=user_id,
    )
    done_ids = completed_task_status_ids()
    if done_ids:
        open_qs = open_qs.exclude(status_id__in=done_ids)
    open_tasks = open_qs.count()

    return {
        'user_id': user_id,
        'email': user.email,
        'tasks_changed': tasks_changed,
        'activity': [
            {
                'action': a['action'],
                'description': a['description'],
                'at': a['created_at'].isoformat() if a['created_at'] else None,
            }
            for a in activity
        ],
        'comments': [
            {
                'task': c['task__title'],
                'preview': (c['content'] or '')[:120],
            }
            for c in comments
        ],
        'github_commits': commits,
        'open_tasks': open_tasks,
    }


def generate_standup_payload(workspace_id: int, hours: int = 24) -> dict:
    since = timezone.now() - timedelta(hours=hours)
    from apps.ai_assistant.models import GitHubWorkspaceConfig

    github_config = GitHubWorkspaceConfig.objects.filter(
        workspace_id=workspace_id,
        is_enabled=True,
    ).first()

    members = TeamMember.objects.filter(workspace_id=workspace_id).select_related('user')
    member_reports = []

    for tm in members:
        if not tm.user_id:
            continue
        ctx = _gather_member_context(
            workspace_id=workspace_id,
            user_id=tm.user_id,
            since=since,
            github_config=github_config,
        )
        if not ctx:
            continue
        member_reports.append(_enrich_with_ai(ctx))

    markdown_lines = ['# Daily standup', f'_Last {hours}h · workspace {workspace_id}_', '']
    for report in member_reports:
        markdown_lines.append(f"## {report.get('email', 'Member')}")
        markdown_lines.append(f"**Yesterday / recent:** {report.get('yesterday', '—')}")
        markdown_lines.append(f"**Today:** {report.get('today', '—')}")
        markdown_lines.append(f"**Blockers:** {report.get('blockers', 'None')}")
        if report.get('github_commits'):
            markdown_lines.append(
                f"**GitHub ({len(report['github_commits'])} commits):** "
                + ', '.join(c.get('message', '')[:40] for c in report['github_commits'][:3])
            )
        markdown_lines.append('')

    return {
        'period_hours': hours,
        'generated_at': timezone.now().isoformat(),
        'members': member_reports,
        'summary_markdown': '\n'.join(markdown_lines),
    }


def _enrich_with_ai(ctx: dict) -> dict:
    """Add yesterday/today/blockers via Groq or rule-based fallback."""
    client = GroqClient()
    payload_json = json.dumps(ctx, default=str)

    if client.is_configured():
        try:
            raw = client.chat(
                system=(
                    'You are a daily standup assistant. Given task activity, comments, and GitHub '
                    'commits, output JSON only with keys: yesterday, today, blockers (short sentences). '
                    'Use the member email as context. If no data, say "No recorded activity".'
                ),
                user=payload_json,
                json_mode=True,
                max_tokens=400,
                temperature=0.2,
            )
            parsed = json.loads(raw)
            return {**ctx, **parsed}
        except (json.JSONDecodeError, RuntimeError) as exc:
            logger.info('Standup Groq fallback: %s', exc)

    commits = ctx.get('github_commits') or []
    activity = ctx.get('activity') or []
    yesterday_parts = []
    if commits:
        yesterday_parts.append(f"{len(commits)} GitHub commit(s)")
    if activity:
        yesterday_parts.append(f"{len(activity)} task update(s)")
    if ctx.get('comments'):
        yesterday_parts.append(f"{len(ctx['comments'])} comment(s)")

    return {
        **ctx,
        'yesterday': ', '.join(yesterday_parts) if yesterday_parts else 'No recorded activity',
        'today': f"Continue work on {ctx.get('open_tasks', 0)} open task(s)",
        'blockers': 'None identified' if ctx.get('open_tasks', 0) < 15 else 'High task load — review priorities',
    }

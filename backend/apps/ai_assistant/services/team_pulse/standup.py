"""Daily standup: DB activity + GitHub commits + optional Groq narrative."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.comments.models import ActivityLog, Comment
from apps.tasks.models import Task
from apps.tasks.status_utils import completed_task_status_ids
from apps.workspaces.models import TeamMember

from ..groq_client import GroqClient
from .github_client import fetch_member_commits

logger = logging.getLogger(__name__)
User = get_user_model()


def _iso_dt(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


def _standup_field_text(value) -> str:
    """Turn AI output (string, list, or dict) into readable markdown prose."""
    if value is None:
        return ''
    if isinstance(value, str):
        text = value.strip()
        if text.startswith('{') or text.startswith('['):
            try:
                return _standup_field_text(json.loads(text))
            except json.JSONDecodeError:
                pass
        return text
    if isinstance(value, list):
        lines = []
        for item in value:
            line = _standup_field_text(item)
            if line:
                lines.append(line if line.startswith('- ') else f'- {line}')
        return '\n'.join(lines)
    if isinstance(value, dict):
        sections = []
        labels = {
            'tasks': 'Tasks',
            'activity': 'Activity',
            'commits': 'GitHub commits',
            'comments': 'Comments',
            'blockers': 'Blockers',
        }
        for key, label in labels.items():
            if key not in value or not value[key]:
                continue
            block = _standup_field_text(value[key])
            if block:
                sections.append(f'**{label}**\n{block}')
        if sections:
            return '\n\n'.join(sections)
        for key, nested in value.items():
            block = _standup_field_text(nested)
            if block:
                title = str(key).replace('_', ' ').strip().title()
                sections.append(f'**{title}**\n{block}')
        return '\n\n'.join(sections)
    text = str(value).strip()
    return text


def _format_github_bullets(commits: list[dict], limit: int = 8) -> str:
    if not commits:
        return ''
    lines = []
    for commit in commits[:limit]:
        message = (commit.get('message') or 'Commit').strip()
        repo = (commit.get('repo') or '').strip()
        suffix = f' (`{repo}`)' if repo else ''
        lines.append(f'- {message}{suffix}')
    return '\n'.join(lines)


def _rule_based_standup_fields(ctx: dict) -> dict[str, str]:
    commits = ctx.get('github_commits') or []
    activity = ctx.get('activity') or []
    comments = ctx.get('comments') or []
    tasks_changed = ctx.get('tasks_changed') or []
    open_count = int(ctx.get('open_tasks') or 0)

    yesterday_lines = []
    if tasks_changed:
        yesterday_lines.append('**Tasks updated**')
        for task in tasks_changed[:8]:
            title = (task.get('title') or 'Task').strip()
            status = (task.get('status') or '').strip()
            yesterday_lines.append(f'- {title}' + (f' ({status})' if status else ''))
    if activity:
        yesterday_lines.append('**Activity**')
        for item in activity[:6]:
            desc = (item.get('description') or item.get('action') or 'Update').strip()
            yesterday_lines.append(f'- {desc}')
    if comments:
        yesterday_lines.append('**Comments**')
        for comment in comments[:4]:
            task = (comment.get('task') or 'Task').strip()
            preview = (comment.get('preview') or '').strip()
            yesterday_lines.append(f'- On *{task}*: {preview}' if preview else f'- On *{task}*')
    if commits:
        yesterday_lines.append('**GitHub**')
        yesterday_lines.extend(_format_github_bullets(commits, limit=6).split('\n'))

    yesterday = '\n\n'.join(yesterday_lines) if yesterday_lines else 'No recorded activity in the last 24 hours.'

    today_lines = []
    if open_count:
        today_lines.append(f'Focus on **{open_count} open task(s)** assigned to you.')
    else:
        today_lines.append('No open tasks — pick up new work or help unblock teammates.')
    if tasks_changed:
        today_lines.append('Continue or close items you touched recently.')

    blockers = 'None identified.'
    if open_count >= 12:
        blockers = f'High workload: **{open_count} open tasks** — consider reprioritizing or asking for help.'

    return {
        'yesterday': yesterday,
        'today': '\n\n'.join(today_lines),
        'blockers': blockers,
    }


def _member_to_markdown(report: dict) -> str:
    email = report.get('email') or 'Team member'
    lines = [f'## {email}', '']

    for heading, key in (
        ('Yesterday', 'yesterday'),
        ('Today', 'today'),
        ('Blockers', 'blockers'),
    ):
        body = _standup_field_text(report.get(key)) or '—'
        lines.extend([f'### {heading}', '', body, ''])

    commits = report.get('github_commits') or []
    gh_block = _format_github_bullets(commits)
    if gh_block and '**GitHub**' not in _standup_field_text(report.get('yesterday')):
        lines.extend(['### GitHub', '', gh_block, ''])

    return '\n'.join(lines).rstrip() + '\n'


def _gather_member_context(
    *,
    organization_id: int,
    user_id: int,
    since,
    github_config,
) -> dict:
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return {}

    tasks_changed = [
        {
            'title': row['title'],
            'status': row['status__name'],
            'updated_at': _iso_dt(row['updated_at']),
            'created_at': _iso_dt(row['created_at']),
        }
        for row in Task.objects.filter(
            project__organization_id=organization_id,
            assigned_to_id=user_id,
        )
        .filter(Q(updated_at__gte=since) | Q(created_at__gte=since))
        .values('title', 'status__name', 'updated_at', 'created_at')[:20]
    ]

    activity = list(
        ActivityLog.objects.filter(
            task__project__organization_id=organization_id,
            user_id=user_id,
            created_at__gte=since,
        )
        .select_related('task')
        .order_by('-created_at')[:15]
        .values('action', 'description', 'created_at')
    )

    comments = list(
        Comment.objects.filter(
            task__project__organization_id=organization_id,
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
        project__organization_id=organization_id,
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


def generate_standup_payload(organization_id: int, hours: int = 24) -> dict:
    since = timezone.now() - timedelta(hours=hours)
    from apps.ai_assistant.models import GitHubOrganizationConfig
    from apps.organizations.models import OrganizationMember

    github_config = GitHubOrganizationConfig.objects.filter(
        organization_id=organization_id,
        is_enabled=True,
    ).first()

    members = OrganizationMember.objects.filter(organization_id=organization_id).select_related('user')
    if not members.exists():
        members = TeamMember.objects.filter(workspace__organization_id=organization_id).select_related('user')
    member_reports = []

    for tm in members:
        if not tm.user_id:
            continue
        ctx = _gather_member_context(
            organization_id=organization_id,
            user_id=tm.user_id,
            since=since,
            github_config=github_config,
        )
        if not ctx:
            continue
        member_reports.append(_enrich_with_ai(ctx))

    markdown_lines = [
        '# Daily standup',
        '',
        f'Period: last **{hours} hours** · organization **{organization_id}**',
        '',
    ]
    for report in member_reports:
        markdown_lines.append(_member_to_markdown(report))

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
                    'You are a daily standup assistant. Output JSON with exactly three keys: '
                    'yesterday, today, blockers. Each value MUST be a single string of markdown '
                    'using short paragraphs and bullet lines starting with "- ". '
                    'Never use nested JSON objects or arrays as values. Summarize tasks, activity, '
                    'comments, and github_commits from the input. If nothing happened, use '
                    '"No recorded activity." for yesterday.'
                ),
                user=payload_json,
                json_mode=True,
                max_tokens=600,
                temperature=0.2,
            )
            parsed = json.loads(raw)
            fields = _rule_based_standup_fields(ctx)
            for key in ('yesterday', 'today', 'blockers'):
                raw = parsed.get(key)
                if raw is not None:
                    fields[key] = _standup_field_text(raw) or fields[key]
            return {**ctx, **fields}
        except (json.JSONDecodeError, RuntimeError) as exc:
            logger.info('Standup Groq fallback: %s', exc)

    return {**ctx, **_rule_based_standup_fields(ctx)}

from __future__ import annotations

import json
import re
from typing import Any

_CATEGORY_PREFIX: dict[str, str] = {
    'architecture': 'ARCH',
    'backend': 'BE',
    'frontend': 'FE',
    'db': 'DB',
    'api': 'API',
    'auth': 'AUTH',
    'middleware': 'MIDDLEWARE',
    'cache': 'CACHE',
    'ai': 'AI',
    'async': 'ASYNC',
    'multi-tenancy': 'MT',
    'testing': 'TEST',
    'ci': 'CI',
    'docs': 'DOC',
    'security': 'SEC',
    'project-management': 'PM',
}


def _slug_from_title(title: str) -> str | None:
    match = re.search(r'\b([A-Za-z]{2,12}-\d{1,3})\b', title or '')
    return match.group(1).upper() if match else None


def ensure_task_slug(task: dict[str, Any], *, sprint_number: int, index: int) -> str:
    """Return a stable slug; mutates task with slug/title when missing."""
    raw = task.get('slug') or task.get('id') or task.get('task_id')
    if raw:
        slug = str(raw).strip().upper()
    else:
        slug = _slug_from_title(str(task.get('title', '')))
    if not slug:
        category = str(task.get('category', 'task')).lower().replace(' ', '-')
        prefix = _CATEGORY_PREFIX.get(category, 'TASK')
        slug = f'{prefix}-{sprint_number:02d}{index:02d}'
    task['slug'] = slug
    if not task.get('title'):
        task['title'] = slug
    elif slug not in str(task['title']):
        task['title'] = f'{slug}: {task["title"]}'
    return slug


def normalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Ensure every task has slug/title; dedupe slugs within the plan."""
    seen: set[str] = set()
    for sprint in plan.get('sprints', []):
        sprint_number = int(sprint.get('sprint_number') or 1)
        tasks = sprint.get('tasks')
        if not isinstance(tasks, list):
            sprint['tasks'] = []
            continue
        for index, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                continue
            slug = ensure_task_slug(task, sprint_number=sprint_number, index=index)
            base = slug
            suffix = 2
            while slug in seen:
                slug = f'{base}-{suffix}'
                suffix += 1
                task['slug'] = slug
            seen.add(slug)
    return plan


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = (raw or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('LLM response must be a JSON object.')
    return data

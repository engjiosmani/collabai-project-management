from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_category_index(team_members: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Map task category -> user_ids whose job_role covers that category."""
    index: dict[str, list[int]] = defaultdict(list)
    for member in team_members:
        user_id = member.get('user_id')
        if not user_id:
            continue
        for category in member.get('task_categories') or []:
            index[category.lower()].append(user_id)
    return index


def pick_assignee_for_category(
    category: str,
    category_index: dict[str, list[int]],
    *,
    round_robin_counters: dict[str, int] | None = None,
) -> int | None:
    """Pick a user_id for a task category; round-robin among eligible members."""
    key = (category or '').lower()
    candidates = category_index.get(key, [])
    if not candidates:
        return None
    if round_robin_counters is None:
        return candidates[0]
    counter = round_robin_counters.get(key, 0)
    user_id = candidates[counter % len(candidates)]
    round_robin_counters[key] = counter + 1
    return user_id


def apply_job_role_assignments(
    plan: dict[str, Any],
    team_members: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Fill missing or invalid suggested_assignee_user_id using job_role task_categories.
    team_members items: user_id, role (display name), task_categories (list).
    """
    if not team_members:
        return plan

    valid_ids = {m['user_id'] for m in team_members if m.get('user_id')}
    category_index = build_category_index(team_members)
    counters: dict[str, int] = {}

    for sprint in plan.get('sprints', []):
        for task in sprint.get('tasks', []):
            category = (task.get('category') or '').lower()
            role_name = task.get('suggested_assignee_role') or ''
            current_id = task.get('suggested_assignee_user_id')

            if current_id not in valid_ids:
                current_id = None

            if current_id is None:
                picked = pick_assignee_for_category(
                    category, category_index, round_robin_counters=counters
                )
                if picked:
                    task['suggested_assignee_user_id'] = picked
                    member = next(
                        (m for m in team_members if m['user_id'] == picked),
                        None,
                    )
                    if member and not role_name:
                        task['suggested_assignee_role'] = member.get('role', '')

            if not task.get('suggested_assignee_role') and task.get('suggested_assignee_user_id'):
                member = next(
                    (m for m in team_members if m['user_id'] == task['suggested_assignee_user_id']),
                    None,
                )
                if member:
                    task['suggested_assignee_role'] = member.get('role', '')

    return plan

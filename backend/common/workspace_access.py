"""Helpers for workspace-scoped access (multi-tenancy via organization → workspace → project)."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.workspaces.models import TeamMember, Workspace


def resolve_workspace(obj):
    """Return the Workspace governing access for Project, Task, Comment, or ActivityLog."""
    if isinstance(obj, Workspace):
        return obj
    ws = getattr(obj, 'workspace', None)
    if ws is not None:
        return ws
    project = getattr(obj, 'project', None)
    if project is not None:
        return project.workspace
    task = getattr(obj, 'task', None)
    if task is not None:
        return task.project.workspace
    return None


def workspaces_queryset_for_user(user) -> QuerySet[Workspace]:
    if getattr(user, 'is_superuser', False):
        return Workspace.objects.all()
    return Workspace.objects.filter(team_members__user=user).distinct()


def user_can_access_workspace(user, workspace) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if workspace is None:
        return False
    return TeamMember.objects.filter(workspace=workspace, user=user).exists()
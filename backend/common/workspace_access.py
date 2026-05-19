"""Workspace-scoped access helpers for legacy workspace APIs."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.workspaces.models import TeamMember, Workspace
from common.tenant_access import (
    organizations_queryset_for_user,
    resolve_organization,
    user_can_access_organization,
)


def resolve_workspace(obj):
    if isinstance(obj, Workspace):
        return obj
    workspace = getattr(obj, 'workspace', None)
    if workspace is not None:
        return workspace
    return None


def workspaces_queryset_for_user(user) -> QuerySet[Workspace]:
    if not user or not user.is_authenticated:
        return Workspace.objects.none()
    if getattr(user, 'is_superuser', False):
        return Workspace.objects.all()
    return Workspace.objects.filter(team_members__user=user).distinct()


def user_can_access_workspace(user, workspace) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    workspace = resolve_workspace(workspace)
    if workspace is None:
        return False
    return TeamMember.objects.filter(workspace=workspace, user=user).exists()

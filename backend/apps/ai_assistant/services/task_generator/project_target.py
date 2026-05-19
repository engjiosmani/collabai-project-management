from __future__ import annotations

from apps.projects.models import Project
from common.workspace_access import user_can_access_workspace


def resolve_target_project(
    *,
    workspace_id: int,
    project_id: int | None,
    user,
    request=None,
) -> Project | None:
    """Return a project in the workspace the user may write to, or None for a new project."""
    if not project_id:
        return None

    if not user or not getattr(user, 'is_authenticated', False):
        raise PermissionError('Authentication required.')

    project = Project.objects.filter(pk=project_id, workspace_id=workspace_id).first()
    if project is None:
        raise ValueError('Project not found in this workspace.')

    workspace_ids = getattr(request, 'workspace_ids', None) if request is not None else None
    if workspace_ids is not None:
        if int(workspace_id) not in {int(wid) for wid in workspace_ids}:
            raise PermissionError('You do not have access to this workspace.')
    elif not user_can_access_workspace(user, project.workspace):
        raise PermissionError('You do not have access to this project.')
    return project

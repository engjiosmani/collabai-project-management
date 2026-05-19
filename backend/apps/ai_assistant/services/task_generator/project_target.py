from __future__ import annotations

from apps.projects.models import Project
from common.tenant_access import user_can_access_organization


def resolve_target_project(
    *,
    organization_id: int,
    project_id: int | None,
    user,
    request=None,
) -> Project | None:
    """Return a project in the organization the user may write to, or None for a new project."""
    if not project_id:
        return None

    if not user or not getattr(user, 'is_authenticated', False):
        raise PermissionError('Authentication required.')

    project = Project.objects.filter(pk=project_id, organization_id=organization_id).first()
    if project is None:
        raise ValueError('Project not found in this organization.')

    org_ids = getattr(request, 'organization_ids', None) if request is not None else None
    if org_ids is not None:
        if int(organization_id) not in {int(oid) for oid in org_ids}:
            raise PermissionError('You do not have access to this organization.')
    elif not user_can_access_organization(user, project.organization):
        raise PermissionError('You do not have access to this project.')
    return project

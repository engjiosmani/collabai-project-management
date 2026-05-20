"""Organization-scoped access helpers."""

from __future__ import annotations

from django.db.models import QuerySet
from apps.organizations.models import Organization, OrganizationMember


def resolve_organization(obj):
    if obj is None:
        return None

    if isinstance(obj, Organization):
        return obj

    # direct organization field
    organization = getattr(obj, 'organization', None)
    if organization is not None:
        return organization

    # workspace -> organization
    workspace = getattr(obj, 'workspace', None)
    if workspace is not None:
        return getattr(workspace, 'organization', None)

    # project relation
    project = getattr(obj, 'project', None)
    if project is not None:
        return resolve_organization(project)

    # task relation
    task = getattr(obj, 'task', None)
    if task is not None:
        return resolve_organization(task)

    return None


def organizations_queryset_for_user(user) -> QuerySet[Organization]:
    if not user or not user.is_authenticated:
        return Organization.objects.none()

    if getattr(user, 'is_superuser', False):
        return Organization.objects.all()

    return Organization.objects.filter(
        members__user=user
    ).distinct()


def user_can_access_organization(user, organization) -> bool:
    if not user or not user.is_authenticated:
        return False

    if getattr(user, 'is_superuser', False):
        return True

    if organization is None:
        return False

    if not isinstance(organization, Organization):
        organization = resolve_organization(organization)

    if organization is None:
        return False

    return OrganizationMember.objects.filter(
        organization=organization,
        user=user,
    ).exists()


resolve_workspace = resolve_organization
workspaces_queryset_for_user = organizations_queryset_for_user
user_can_access_workspace = user_can_access_organization
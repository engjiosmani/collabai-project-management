"""Organization-scoped access (replaces workspace in product APIs)."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.organizations.models import Organization, OrganizationMember


def resolve_organization(obj):
    if isinstance(obj, Organization):
        return obj
    org = getattr(obj, 'organization', None)
    if org is not None:
        return org
    workspace = getattr(obj, 'workspace', None)
    if workspace is not None:
        return getattr(workspace, 'organization', None)
    project = getattr(obj, 'project', None)
    if project is not None:
        return getattr(project, 'organization', None)
    task = getattr(obj, 'task', None)
    if task is not None:
        return task.project.organization
    return None


def organizations_queryset_for_user(user) -> QuerySet[Organization]:
    if not user or not user.is_authenticated:
        return Organization.objects.none()
    if getattr(user, 'is_superuser', False):
        return Organization.objects.all()

    from django.db.models import Q
    from apps.workspaces.models import TeamMember

    org_ids_via_team = TeamMember.objects.filter(user=user).values_list(
        'workspace__organization_id', flat=True
    )

    return Organization.objects.filter(
        Q(members__user=user) | Q(pk__in=org_ids_via_team)
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
    if OrganizationMember.objects.filter(organization=organization, user=user).exists():
        return True
    # Legacy workspace memberships until data is fully migrated
    from apps.workspaces.models import TeamMember

    return TeamMember.objects.filter(
        workspace__organization=organization,
        user=user,
    ).exists()


# Backward-compatible aliases for gradual migration
resolve_workspace = resolve_organization
workspaces_queryset_for_user = organizations_queryset_for_user
user_can_access_workspace = user_can_access_organization

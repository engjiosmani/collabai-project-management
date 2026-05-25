"""Organization-scoped access helpers."""

from __future__ import annotations

from django.db.models import QuerySet
from apps.organizations.models import Organization, OrganizationMember

TENANT_HEADER = 'HTTP_X_ORGANIZATION_ID'


def resolve_organization(obj):
    """Resolve organization from an object.

    Supports direct organization fields and common project/task ownership chains.
    """
    if obj is None:
        return None

    if isinstance(obj, Organization):
        return obj

    # direct organization field
    organization = getattr(obj, 'organization', None)
    if organization is not None:
        return organization

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
    """Get all organizations the user is a member of."""
    if not user or not user.is_authenticated:
        return Organization.objects.none()

    if getattr(user, 'is_superuser', False):
        return Organization.objects.all()

    return Organization.objects.filter(
        members__user=user
    ).distinct()


def user_can_access_organization(user, organization) -> bool:
    """Check if user has access to an organization.

    Access is determined by OrganizationMember status.
    """
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


def normalize_organization_id(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def active_organization_id_from_request(request) -> int | None:
    """Return requested active tenant id from header or query params."""
    header_value = request.META.get(TENANT_HEADER)
    query_value = getattr(request, 'query_params', {}).get('organization_id')
    return normalize_organization_id(header_value or query_value)


def organization_ids_for_request(request) -> list[int]:
    """Authorized tenant ids for this request, narrowed to active tenant when provided."""
    if getattr(request, 'invalid_requested_organization_id', False):
        return []
    requested = getattr(request, 'requested_organization_id', None)
    if requested:
        return [requested]
    return list(getattr(request, 'organization_ids', []) or [])

from rest_framework.permissions import BasePermission

from apps.organizations.models import OrganizationMember
from common.tenant_access import resolve_organization


def _user_has_org_role(user, organization, allowed_roles) -> bool:
    if not user or not user.is_authenticated or organization is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return OrganizationMember.objects.filter(
        organization=organization,
        user=user,
        role__in=allowed_roles,
    ).exists()


class IsAdmin(BasePermission):
    """Organization admin (membership role = admin) for the resource's organization."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        organization = resolve_organization(obj)
        return _user_has_org_role(
            request.user, organization, (OrganizationMember.ADMIN,)
        )


class IsManagerOrAdmin(BasePermission):
    """Organization admin or manager for the resource's organization."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        organization = resolve_organization(obj)
        return _user_has_org_role(
            request.user,
            organization,
            (OrganizationMember.ADMIN, OrganizationMember.MANAGER),
        )
from rest_framework.permissions import BasePermission

from apps.organizations.models import OrganizationMember
from common.tenant_access import resolve_organization


def _resolve_workspace(obj):
    """Try to resolve a Workspace from an object."""
    from apps.workspaces.models import Workspace
    if isinstance(obj, Workspace):
        return obj
    ws = getattr(obj, 'workspace', None)
    if ws is not None:
        return ws
    return None


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


def _user_has_workspace_role(user, workspace, allowed_roles) -> bool:
    if not user or not user.is_authenticated or workspace is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    from apps.workspaces.models import TeamMember
    return TeamMember.objects.filter(
        workspace=workspace,
        user=user,
        role__in=allowed_roles,
    ).exists()


class IsOrgAdmin(BasePermission):
    """User must have the org_admin role in the resource's organization."""

    message = 'You must be an organization admin to perform this action.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        organization = resolve_organization(obj)
        return _user_has_org_role(
            request.user, organization, (OrganizationMember.ORG_ADMIN,)
        )


class IsWorkspaceAdmin(BasePermission):
    """User must have workspace_admin role in the resource's workspace.

    Falls back to org_admin check when no workspace can be resolved from the object.
    """

    message = 'You must be a workspace admin to perform this action.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from apps.workspaces.models import TeamMember
        workspace = _resolve_workspace(obj)
        if workspace is not None:
            return _user_has_workspace_role(
                request.user, workspace, (TeamMember.WORKSPACE_ADMIN,)
            )
        organization = resolve_organization(obj)
        return _user_has_org_role(
            request.user, organization, (OrganizationMember.ORG_ADMIN,)
        )


class IsManagerOrAbove(BasePermission):
    """User must have workspace_admin or manager role in the resource's workspace.

    Falls back to org_admin check when no workspace can be resolved.
    """

    message = 'You must be a manager or above to perform this action.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from apps.workspaces.models import TeamMember
        workspace = _resolve_workspace(obj)
        if workspace is not None:
            return _user_has_workspace_role(
                request.user,
                workspace,
                (TeamMember.WORKSPACE_ADMIN, TeamMember.MANAGER),
            )
        organization = resolve_organization(obj)
        return _user_has_org_role(
            request.user, organization, (OrganizationMember.ORG_ADMIN,)
        )


class IsMember(BasePermission):
    """User must be any member of the resource's organization."""

    message = 'You do not have access to this resource.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from common.tenant_access import user_can_access_organization
        user = request.user
        if getattr(user, 'is_superuser', False):
            return True
        organization = resolve_organization(obj)
        return user_can_access_organization(user, organization)


# Backward-compatibility aliases
IsAdmin = IsOrgAdmin
IsManagerOrAdmin = IsManagerOrAbove
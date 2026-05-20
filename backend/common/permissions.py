from rest_framework.permissions import SAFE_METHODS, BasePermission
from common.tenant_access import resolve_organization, user_can_access_organization

resolve_workspace = resolve_organization
user_can_access_workspace = user_can_access_organization


def user_matches_any_required_role(user, required_roles):
    """True if Django auth user satisfies any required role."""
    if not user or not user.is_authenticated:
        return False

    roles = tuple(required_roles or ())
    if not roles:
        return True

    inner = getattr(user, 'role', None)
    if inner is not None:
        if inner in roles:
            return True

        name = getattr(inner, 'name', None)
        if name is not None and name in roles:
            return True

    groups = getattr(user, 'groups', None)
    if groups is not None and groups.filter(name__in=roles).exists():
        return True

    return False


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        owner = getattr(obj, 'user', None)
        return owner is not None and owner == user


class IsAuthenticatedReadOnly(BasePermission):
    """Authenticated users can read; only staff can modify."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if request.method in SAFE_METHODS:
            return bool(user and user.is_authenticated)

        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'is_staff', False)
        )


class IsOrganizationMember(BasePermission):
    """Read/write when user belongs to the object's organization."""

    message = 'You do not have access to this resource.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if getattr(user, 'is_superuser', False):
            return True

        organization = resolve_organization(obj)
        return user_can_access_organization(user, organization)


# backward compatibility
IsWorkspaceTeamMember = IsOrganizationMember


class IsWorkspaceMemberCommentAuthorForWrite(BasePermission):
    """
    Safe methods:
    organization members can read.

    Unsafe methods:
    only comment author can modify.
    """

    message = 'You do not have permission to modify this comment.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if getattr(user, 'is_superuser', False):
            return True

        organization = resolve_organization(obj)

        if not user_can_access_organization(user, organization):
            return False

        if request.method in SAFE_METHODS:
            return True

        return obj.author_id == user.id


class HasRole(BasePermission):
    required_role = None

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        required_role = getattr(view, 'required_role', self.required_role)

        if not required_role:
            return bool(user and user.is_authenticated)

        return user_matches_any_required_role(user, (required_role,))


class HasAnyRole(BasePermission):
    required_roles = ()

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        required_roles = tuple(
            getattr(view, 'required_roles', self.required_roles) or ()
        )

        return user_matches_any_required_role(user, required_roles)
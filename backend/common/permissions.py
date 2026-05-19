from rest_framework.permissions import SAFE_METHODS, BasePermission
from common.tenant_access import resolve_organization, user_can_access_organization

resolve_workspace = resolve_organization
user_can_access_workspace = user_can_access_organization

def user_matches_any_required_role(user, required_roles):
    """True if Django auth user satisfies any identifier in ``required_roles`` (names/slugs or objects).

    Mirrors view-level RBAC logic used by HasRole / HasAnyRole so middleware and DRF agree.
    """
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

    profile = getattr(user, 'profile', None)
    if profile and getattr(profile, 'role', None) is not None:
        pname = getattr(profile.role, 'name', None)
        if pname is not None and pname in roles:
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
    """Allow authenticated users to read, but reserve unsafe methods for admins."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if request.method in SAFE_METHODS:
            return bool(user and user.is_authenticated)
        return bool(user and user.is_authenticated and getattr(user, 'is_staff', False))

class IsOrganizationMember(BasePermission):
    """Read/write when the user belongs to the object's organization."""

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


IsWorkspaceTeamMember = IsOrganizationMember
class IsWorkspaceMemberCommentAuthorForWrite(BasePermission):
    """
    Safe methods: user must be a workspace team member for the comment's task/project.
    Unsafe methods: must be comment author (and still a workspace member).
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


class IsWorkspaceInviteAccess(BasePermission):
    """Invite recipient can view/accept own invite; workspace members manage all invites."""

    message = 'You do not have permission to access this invite.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, 'is_superuser', False):
            return True

        organization = resolve_organization(obj)
        is_member = user_can_access_organization(user, organization)
        user_email = (getattr(user, 'email', '') or '').strip().lower()
        invite_email = (getattr(obj, 'email', '') or '').strip().lower()
        is_recipient = bool(user_email and invite_email and user_email == invite_email)

        if request.method in SAFE_METHODS:
            return is_member or is_recipient

        if getattr(view, 'action', None) == 'accept':
            return is_member or is_recipient

        return is_member

class HasRole(BasePermission):
    required_role = None

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        required_role = getattr(view, 'required_role', self.required_role)
        if not required_role:
            return user is not None and user.is_authenticated
        return user_matches_any_required_role(user, (required_role,))


class HasAnyRole(BasePermission):
    required_roles = ()

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        required_roles = tuple(getattr(view, 'required_roles', self.required_roles) or ())
        return user_matches_any_required_role(user, required_roles)

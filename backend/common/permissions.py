from rest_framework.permissions import BasePermission


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

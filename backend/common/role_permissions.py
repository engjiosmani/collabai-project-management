from rest_framework.permissions import BasePermission

from apps.workspaces.models import Role
from common.roles import get_user_role


class IsAdmin(BasePermission):

    def has_permission(self, request, view):

        workspace = getattr(
            request,
            "workspace",
            None
        )

        if not workspace:
            return False

        role = get_user_role(
            request.user,
            workspace
        )

        return role == Role.ADMIN


class IsManagerOrAdmin(BasePermission):

    def has_permission(self, request, view):

        workspace = getattr(
            request,
            "workspace",
            None
        )

        if not workspace:
            return False

        role = get_user_role(
            request.user,
            workspace
        )

        return role in [
            Role.ADMIN,
            Role.MANAGER
        ]
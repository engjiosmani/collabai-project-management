from django.db.models import Q
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
    project = getattr(obj, 'project', None)
    if project is not None:
        return getattr(project, 'workspace', None)
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


def user_is_org_admin(user, organization) -> bool:
    return _user_has_org_role(
        user,
        organization,
        (OrganizationMember.ORG_ADMIN,),
    )


def user_is_workspace_admin_or_org_admin(user, organization, workspace=None) -> bool:
    if user_is_org_admin(user, organization):
        return True

    if workspace is None and organization is not None:
        from apps.workspaces.models import TeamMember
        return TeamMember.objects.filter(
            workspace__organization=organization,
            user=user,
            role=TeamMember.WORKSPACE_ADMIN,
        ).exists()

    from apps.workspaces.models import TeamMember
    return _user_has_workspace_role(
        user,
        workspace,
        (TeamMember.WORKSPACE_ADMIN,),
    )


def user_is_manager_or_above(user, organization, workspace=None) -> bool:
    if user_is_org_admin(user, organization):
        return True

    from apps.workspaces.models import TeamMember

    allowed_roles = (
        TeamMember.WORKSPACE_ADMIN,
        TeamMember.MANAGER,
    )

    if workspace is None and organization is not None:
        return TeamMember.objects.filter(
            workspace__organization=organization,
            user=user,
            role__in=allowed_roles,
        ).exists()

    return _user_has_workspace_role(user, workspace, allowed_roles)


def user_can_manage_workspace_content(user, workspace, *, allow_manager=True) -> bool:
    """Return True when a user can manage projects/tasks inside one workspace."""
    if workspace is None:
        return False
    if user_is_org_admin(user, workspace.organization):
        return True

    from apps.workspaces.models import TeamMember

    roles = [TeamMember.WORKSPACE_ADMIN]
    if allow_manager:
        roles.append(TeamMember.MANAGER)
    return _user_has_workspace_role(user, workspace, tuple(roles))


def user_can_manage_project(user, project, *, allow_manager=True) -> bool:
    if not project:
        return False
    if user_is_org_admin(user, project.organization):
        return True
    if getattr(project, 'workspace', None) is None:
        return user_is_manager_or_above(user, project.organization)
    return user_can_manage_workspace_content(
        user,
        getattr(project, 'workspace', None),
        allow_manager=allow_manager,
    )


def user_has_project_access(user, project) -> bool:
    """Return True when the user can see a project.

    Org admins and elevated workspace roles can see all projects in the org.
    Regular members must be explicitly attached through ProjectMember.
    """
    if not user or not user.is_authenticated or project is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user_can_manage_project(user, project):
        return True
    return project.members.filter(user=user).exists()


def project_visibility_q(user, organization_ids):
    """Q object for projects visible to user inside already-authorized org ids."""
    from apps.workspaces.models import TeamMember

    if getattr(user, 'is_superuser', False):
        return Q(organization_id__in=organization_ids)

    elevated_org_ids = set(
        OrganizationMember.objects.filter(
            user=user,
            organization_id__in=organization_ids,
            role=OrganizationMember.ORG_ADMIN,
        ).values_list('organization_id', flat=True)
    )

    elevated_workspace_ids = set(
        TeamMember.objects.filter(
            user=user,
            workspace__organization_id__in=organization_ids,
            role__in=(TeamMember.WORKSPACE_ADMIN, TeamMember.MANAGER),
        ).values_list('workspace_id', flat=True)
    )

    q = Q(members__user=user)
    if elevated_org_ids:
        q |= Q(organization_id__in=elevated_org_ids)
    if elevated_workspace_ids:
        q |= Q(workspace_id__in=elevated_workspace_ids)
    return Q(organization_id__in=organization_ids) & q


def task_visibility_q(user, organization_ids):
    """Q object for tasks visible to user inside already-authorized org ids."""
    from apps.projects.models import Project

    visible_projects = Project.objects.filter(
        project_visibility_q(user, organization_ids)
    )
    return (
        Q(project__in=visible_projects)
        | Q(
            project__organization_id__in=organization_ids,
            assigned_to=user,
        )
        | Q(
            project__organization_id__in=organization_ids,
            activity_logs__action='Task created',
            activity_logs__user=user,
        )
    )


def user_can_update_task(user, task) -> bool:
    if not user or not user.is_authenticated or task is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user_can_manage_project(user, task.project):
        return True
    return (
        task.assigned_to_id == user.id
        and OrganizationMember.objects.filter(
            organization=task.project.organization,
            user=user,
        ).exists()
    )


def user_can_assign_task(user, organization) -> bool:
    return user_is_manager_or_above(user, organization)


def user_can_assign_task_in_project(user, project) -> bool:
    return user_can_manage_project(user, project)


def can_workspace_admin_assign_role(request_user, workspace, target_role) -> bool:
    """Workspace admins may assign only lower workspace roles."""
    from apps.workspaces.models import TeamMember

    if user_is_org_admin(request_user, workspace.organization):
        return True
    if not _user_has_workspace_role(
        request_user,
        workspace,
        (TeamMember.WORKSPACE_ADMIN,),
    ):
        return False
    return target_role in (TeamMember.MANAGER, TeamMember.MEMBER)


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
            if user_is_org_admin(request.user, workspace.organization):
                return True
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
            if user_is_org_admin(request.user, workspace.organization):
                return True
            return _user_has_workspace_role(
                request.user,
                workspace,
                (TeamMember.WORKSPACE_ADMIN, TeamMember.MANAGER),
            )
        organization = resolve_organization(obj)
        return user_is_manager_or_above(request.user, organization)


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


# Compatibility aliases for older role names.
IsAdmin = IsOrgAdmin
IsManagerOrAdmin = IsManagerOrAbove

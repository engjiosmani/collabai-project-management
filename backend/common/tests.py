from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from rest_framework.test import APIRequestFactory

from common.permissions import (
    IsOwner,
    HasRole,
    HasAnyRole,
    user_matches_any_required_role,
)
from common.workspace_access import (
    resolve_workspace,
    workspaces_queryset_for_user,
    user_can_access_workspace,
)

from apps.organizations.models import Organization
from apps.workspaces.models import Workspace, TeamMember, Role
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority
from apps.user_profiles.models import Profile

User = get_user_model()


class DummyObj:
    def __init__(self, user=None):
        self.user = user


class DummyView:
    required_role = "Admin"
    required_roles = ("Admin", "Manager")


class CommonTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            email="user@test.com",
            username="user@test.com",
            password="Password123!"
        )

        self.other = User.objects.create_user(
            email="other@test.com",
            username="other@test.com",
            password="Password123!"
        )

    def test_is_owner_true(self):
        request = self.factory.get("/")
        request.user = self.user
        obj = DummyObj(user=self.user)

        self.assertTrue(IsOwner().has_object_permission(request, None, obj))

    def test_is_owner_false(self):
        request = self.factory.get("/")
        request.user = self.user
        obj = DummyObj(user=self.other)

        self.assertFalse(IsOwner().has_object_permission(request, None, obj))

    def test_has_role_without_required_role(self):
        request = self.factory.get("/")
        request.user = self.user

        permission = HasRole()
        self.assertTrue(permission.has_permission(request, None))

    def test_has_any_role_false(self):
        request = self.factory.get("/")
        request.user = self.user

        permission = HasAnyRole()
        self.assertFalse(permission.has_permission(request, DummyView()))

    def test_anonymous_has_no_workspaces(self):
        qs = workspaces_queryset_for_user(AnonymousUser())
        self.assertEqual(qs.count(), 0)

    def test_user_cannot_access_none_workspace(self):
        self.assertFalse(user_can_access_workspace(self.user, None))

    def test_user_matches_role_from_profile(self):
        org = Organization.objects.create(name="Role Org")
        workspace = Workspace.objects.create(name="Role WS", organization=org)
        role = Role.objects.create(name="Admin", workspace=workspace)

        Profile.objects.create(
            user=self.user,
            workspace=workspace,
            role=role
        )

        self.assertTrue(user_matches_any_required_role(self.user, ("Admin",)))

    def test_user_matches_group_role(self):
        group = Group.objects.create(name="Manager")
        self.user.groups.add(group)

        self.assertTrue(user_matches_any_required_role(self.user, ("Manager",)))

    def test_user_does_not_match_required_role(self):
        self.assertFalse(user_matches_any_required_role(self.user, ("Admin",)))

    def test_user_matches_no_required_roles_returns_true(self):
        self.assertTrue(user_matches_any_required_role(self.user, ()))

    def test_workspaces_queryset_for_team_member(self):
        org = Organization.objects.create(name="Access Org")
        workspace = Workspace.objects.create(name="Access WS", organization=org)

        TeamMember.objects.create(
            user=self.user,
            workspace=workspace
        )

        qs = workspaces_queryset_for_user(self.user)

        self.assertIn(workspace, qs)

    def test_user_can_access_workspace_as_team_member(self):
        org = Organization.objects.create(name="Can Access Org")
        workspace = Workspace.objects.create(name="Can Access WS", organization=org)

        TeamMember.objects.create(
            user=self.user,
            workspace=workspace
        )

        self.assertTrue(user_can_access_workspace(self.user, workspace))

    def test_user_cannot_access_workspace_if_not_member(self):
        org = Organization.objects.create(name="Cannot Access Org")
        workspace = Workspace.objects.create(name="Cannot Access WS", organization=org)

        self.assertFalse(user_can_access_workspace(self.user, workspace))



    def test_resolve_workspace_from_project(self):
        org = Organization.objects.create(name="Resolve Org")
        workspace = Workspace.objects.create(name="Resolve WS", organization=org)
        project = Project.objects.create(name="Resolve Project", workspace=workspace)

        self.assertEqual(resolve_workspace(project), workspace)

    def test_resolve_workspace_from_task(self):
        org = Organization.objects.create(name="Resolve Task Org")
        workspace = Workspace.objects.create(name="Resolve Task WS", organization=org)
        project = Project.objects.create(name="Resolve Task Project", workspace=workspace)

        status, _ = TaskStatus.objects.get_or_create(name="To Do")
        priority, _ = TaskPriority.objects.get_or_create(
            level=2,
            defaults={"name": "Medium"}
        )

        task = Task.objects.create(
            project=project,
            title="Resolve Task",
            status=status,
            priority=priority
        )

        self.assertEqual(resolve_workspace(task), workspace)

    def test_resolve_workspace_returns_none_for_unknown_object(self):
        obj = object()

        self.assertIsNone(resolve_workspace(obj))
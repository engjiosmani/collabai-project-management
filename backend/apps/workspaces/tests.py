from django.test import TestCase
from apps.organizations.models import Organization
from .models import Workspace, Role, Permission


class WorkspaceModelTest(TestCase):
    def test_workspace_creation(self):
        org = Organization.objects.create(name="Org")
        workspace = Workspace.objects.create(name="WS", organization=org)

        self.assertEqual(workspace.organization, org)


class RolePermissionTest(TestCase):
    def test_role_permission(self):
        org = Organization.objects.create(name="Org")
        ws = Workspace.objects.create(name="WS", organization=org)

        perm = Permission.objects.create(code="create_task", name="Create Task")
        role = Role.objects.create(name="Admin", workspace=ws)
        role.permissions.add(perm)

        self.assertIn(perm, role.permissions.all())


        from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from .models import Workspace, Role, Permission, TeamMember, WorkspaceInvite

User = get_user_model()


class WorkspaceModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="workspaceuser", password="test12345")
        self.org = Organization.objects.create(name="Workspace Org")
        self.workspace = Workspace.objects.create(name="Main Workspace", organization=self.org)
        self.permission = Permission.objects.create(
            code="create_task",
            name="Create Task",
            description="Can create tasks"
        )
        self.role = Role.objects.create(name="Admin", workspace=self.workspace)
        self.role.permissions.add(self.permission)

    def test_workspace_role_permission_relationship(self):
        self.assertEqual(self.workspace.organization, self.org)
        self.assertIn(self.permission, self.role.permissions.all())

    def test_create_team_member(self):
        team_member = TeamMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=self.role
        )

        self.assertEqual(team_member.workspace, self.workspace)
        self.assertEqual(team_member.user, self.user)
        self.assertEqual(team_member.role, self.role)

    def test_create_workspace_invite(self):
        invite = WorkspaceInvite.objects.create(
            workspace=self.workspace,
            email="invite@test.com",
            role=self.role,
            token="test-token-123"
        )

        self.assertEqual(invite.workspace, self.workspace)
        self.assertEqual(invite.email, "invite@test.com")
        self.assertFalse(invite.is_accepted)


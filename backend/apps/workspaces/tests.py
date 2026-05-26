from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from .models import TeamMember, Workspace

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class WorkspaceModelTest(TestCase):
    def test_workspace_creation(self):
        org = Organization.objects.create(name='Org')
        workspace = Workspace.objects.create(name='WS', organization=org)
        self.assertEqual(workspace.organization, org)


class TeamMemberRoleChoicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tmrole@example.com', password='test12345')
        self.org = Organization.objects.create(name='Role Choices Org')
        self.workspace = Workspace.objects.create(name='Role Choices WS', organization=self.org)

    def test_workspace_admin_role(self):
        tm = TeamMember.objects.create(
            workspace=self.workspace, user=self.user, role=TeamMember.WORKSPACE_ADMIN
        )
        self.assertEqual(tm.role, 'workspace_admin')

    def test_manager_role(self):
        tm = TeamMember.objects.create(
            workspace=self.workspace, user=self.user, role=TeamMember.MANAGER
        )
        self.assertEqual(tm.role, 'manager')

    def test_member_role_is_default(self):
        tm = TeamMember.objects.create(workspace=self.workspace, user=self.user)
        self.assertEqual(tm.role, TeamMember.MEMBER)

    def test_role_choices_count(self):
        self.assertEqual(len(TeamMember.ROLE_CHOICES), 3)

    def test_role_choice_values(self):
        values = [v for v, _ in TeamMember.ROLE_CHOICES]
        self.assertIn('workspace_admin', values)
        self.assertIn('manager', values)
        self.assertIn('member', values)


class WorkspaceModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='workspaceuser', password='test12345')
        self.org = Organization.objects.create(name='Workspace Org')
        self.workspace = Workspace.objects.create(name='Main Workspace', organization=self.org)

    def test_workspace_organization_relation(self):
        self.assertEqual(self.workspace.organization, self.org)

    def test_create_team_member(self):
        team_member = TeamMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=TeamMember.WORKSPACE_ADMIN,
        )
        self.assertEqual(team_member.workspace, self.workspace)
        self.assertEqual(team_member.user, self.user)
        self.assertEqual(team_member.role, TeamMember.WORKSPACE_ADMIN)


class WorkspaceApiTest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username='wmem@example.com', email='wmem@example.com', password='x'
        )
        self.org = Organization.objects.create(name='W Org API')
        self.workspace = Workspace.objects.create(name='W Main', organization=self.org)
        OrganizationMember.objects.create(
            organization=self.org, user=self.member, role=OrganizationMember.MEMBER
        )
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.WORKSPACE_ADMIN
        )

    def test_workspace_crud_and_members(self):
        res = self.client.get('/api/v1/workspaces/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)

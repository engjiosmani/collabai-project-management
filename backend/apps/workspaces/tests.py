import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization
from .models import Permission, Role, TeamMember, Workspace

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class WorkspaceModelTest(TestCase):
    def test_workspace_creation(self):
        org = Organization.objects.create(name='Org')
        workspace = Workspace.objects.create(name='WS', organization=org)
        self.assertEqual(workspace.organization, org)


class RolePermissionTest(TestCase):
    def test_role_permission(self):
        org = Organization.objects.create(name='Org2')
        ws = Workspace.objects.create(name='WS2', organization=org)
        perm = Permission.objects.create(code='create_task', name='Create Task')
        role = Role.objects.create(name=Role.ADMIN, workspace=ws)
        role.permissions.add(perm)
        self.assertIn(perm, role.permissions.all())


class WorkspaceModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='workspaceuser',
            password='test12345'
        )
        self.org = Organization.objects.create(name='Workspace Org')
        self.workspace = Workspace.objects.create(
            name='Main Workspace',
            organization=self.org
        )
        self.permission = Permission.objects.create(
            code='create_task_2',
            name='Create Task'
        )
        self.role = Role.objects.create(
            name=Role.ADMIN,
            workspace=self.workspace
        )
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


@unittest.skip('Workspace REST API removed from product; org-centric routes used instead.')
class WorkspaceApiTest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username='wmem@example.com',
            email='wmem@example.com',
            password='x'
        )
        self.staff = User.objects.create_user(
            username='wstaff@example.com',
            email='wstaff@example.com',
            password='x',
            is_staff=True,
        )

        self.org = Organization.objects.create(name='W Org API')
        self.workspace = Workspace.objects.create(
            name='W Main',
            organization=self.org
        )
        self.permission = Permission.objects.create(
            code='manage_workspaces',
            name='Manage Workspaces'
        )
        self.role = Role.objects.create(
            workspace=self.workspace,
            name=Role.ADMIN
        )
        self.role.permissions.add(self.permission)
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=self.role
        )

    def test_workspace_crud_and_members(self):
        list_res = self.client.get(
            '/api/v1/workspaces/',
            **_jwt_header(self.member)
        )
        self.assertEqual(list_res.status_code, 200)

    def test_role_and_permission_endpoints(self):
        perm_create = self.client.post(
            '/api/v1/permissions/',
            {'code': 'create_reports', 'name': 'Create Reports'},
            format='json',
            **_jwt_header(self.staff),
        )
        self.assertEqual(perm_create.status_code, 201)
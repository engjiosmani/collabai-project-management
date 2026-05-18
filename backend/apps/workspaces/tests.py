from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization

from .models import Permission, Role, TeamMember, Workspace, WorkspaceInvite

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
        role = Role.objects.create(name='Admin', workspace=ws)
        role.permissions.add(perm)
        self.assertIn(perm, role.permissions.all())


class WorkspaceModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='workspaceuser', password='test12345')
        self.org = Organization.objects.create(name='Workspace Org')
        self.workspace = Workspace.objects.create(name='Main Workspace', organization=self.org)
        self.permission = Permission.objects.create(code='create_task_2', name='Create Task')
        self.role = Role.objects.create(name='Admin', workspace=self.workspace)
        self.role.permissions.add(self.permission)

    def test_workspace_role_permission_relationship(self):
        self.assertEqual(self.workspace.organization, self.org)
        self.assertIn(self.permission, self.role.permissions.all())

    def test_create_team_member(self):
        team_member = TeamMember.objects.create(workspace=self.workspace, user=self.user, role=self.role)
        self.assertEqual(team_member.workspace, self.workspace)
        self.assertEqual(team_member.user, self.user)
        self.assertEqual(team_member.role, self.role)

    def test_create_workspace_invite(self):
        invite = WorkspaceInvite.objects.create(
            workspace=self.workspace,
            email='invite@test.com',
            role=self.role,
            token='test-token-123',
        )
        self.assertEqual(invite.workspace, self.workspace)
        self.assertEqual(invite.email, 'invite@test.com')
        self.assertFalse(invite.is_accepted)


class WorkspaceApiTest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='wmem@example.com', email='wmem@example.com', password='x')
        self.staff = User.objects.create_user(
            username='wstaff@example.com',
            email='wstaff@example.com',
            password='x',
            is_staff=True,
        )
        self.invited = User.objects.create_user(username='invitee@example.com', email='invitee@example.com', password='x')

        self.org = Organization.objects.create(name='W Org API')
        self.workspace = Workspace.objects.create(name='W Main', organization=self.org)
        self.permission = Permission.objects.create(code='manage_workspaces', name='Manage Workspaces')
        self.role = Role.objects.create(workspace=self.workspace, name='Owner')
        self.role.permissions.add(self.permission)
        TeamMember.objects.create(workspace=self.workspace, user=self.member, role=self.role)

    def test_workspace_crud_and_members(self):
        list_res = self.client.get('/api/v1/workspaces/', **_jwt_header(self.member))
        self.assertEqual(list_res.status_code, 200)

        create_res = self.client.post(
            '/api/v1/workspaces/',
            {'organization': self.org.pk, 'name': 'W Secondary', 'is_active': True},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(create_res.status_code, 201, create_res.data)
        wid = create_res.data['id']

        members_res = self.client.get(f'/api/v1/workspaces/{wid}/members/', **_jwt_header(self.member))
        self.assertEqual(members_res.status_code, 200)
        self.assertGreaterEqual(len(members_res.data), 1)

        update_res = self.client.patch(
            f'/api/v1/workspaces/{wid}/',
            {'name': 'W Secondary Updated'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(update_res.status_code, 200)

    def test_role_and_permission_endpoints(self):
        perm_create = self.client.post(
            '/api/v1/permissions/',
            {'code': 'create_reports', 'name': 'Create Reports'},
            format='json',
            **_jwt_header(self.staff),
        )
        self.assertEqual(perm_create.status_code, 201, perm_create.data)

        perm_non_staff = self.client.post(
            '/api/v1/permissions/',
            {'code': 'x_non_staff', 'name': 'X'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(perm_non_staff.status_code, 403)

        role_create = self.client.post(
            '/api/v1/roles/',
            {'workspace': self.workspace.pk, 'name': 'Contributor', 'permissions': [self.permission.pk]},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(role_create.status_code, 201, role_create.data)

        role_list = self.client.get('/api/v1/roles/?workspace=%s' % self.workspace.pk, **_jwt_header(self.member))
        self.assertEqual(role_list.status_code, 200)

    def test_invite_create_and_accept(self):
        invite_res = self.client.post(
            '/api/v1/invites/',
            {'workspace': self.workspace.pk, 'email': self.invited.email, 'role': self.role.pk},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(invite_res.status_code, 201, invite_res.data)
        iid = invite_res.data['id']

        # Recipient can retrieve and accept the invite before being a team member.
        retrieve_res = self.client.get(f'/api/v1/invites/{iid}/', **_jwt_header(self.invited))
        self.assertEqual(retrieve_res.status_code, 200)

        accept_res = self.client.post(f'/api/v1/invites/{iid}/accept/', **_jwt_header(self.invited))
        self.assertEqual(accept_res.status_code, 200, accept_res.data)
        self.assertTrue(accept_res.data['invite']['is_accepted'])
        self.assertTrue(TeamMember.objects.filter(workspace=self.workspace, user=self.invited).exists())



from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization
from apps.workspaces.models import Role, TeamMember, Workspace
from .models import Profile

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class ProfileModelTest(TestCase):
    def test_profile_creation(self):
        user = User.objects.create(username="testuser")
        org = Organization.objects.create(name="Org")
        ws = Workspace.objects.create(name="WS", organization=org)

        profile = Profile.objects.create(user=user, workspace=ws)

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.workspace, ws)


class UserProfileApiTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1@example.com', email='u1@example.com', password='x')
        self.other = User.objects.create_user(username='u2@example.com', email='u2@example.com', password='x')
        self.third = User.objects.create_user(username='u3@example.com', email='u3@example.com', password='x')

        self.org = Organization.objects.create(name='Users Org')
        self.ws = Workspace.objects.create(name='Users WS', organization=self.org)
        self.role = Role.objects.create(workspace=self.ws, name='Member')
        TeamMember.objects.create(workspace=self.ws, user=self.user, role=self.role)
        TeamMember.objects.create(workspace=self.ws, user=self.other, role=self.role)

    def test_workspace_scoped_user_listing(self):
        res = self.client.get('/api/v1/users/?search=u2@example.com', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 200)
        emails = [item['email'] for item in res.data.get('results', res.data)]
        self.assertIn('u2@example.com', emails)
        self.assertNotIn('u3@example.com', emails)

    def test_me_endpoint_get_and_patch(self):
        get_res = self.client.get('/api/v1/users/me/', **_jwt_header(self.user))
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.data['email'], 'u1@example.com')

        patch_res = self.client.patch(
            '/api/v1/users/me/',
            {
                'first_name': 'Updated',
                'bio': 'Developer',
                'workspace': self.ws.pk,
                'role': self.role.pk,
            },
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(patch_res.status_code, 200, patch_res.data)
        self.assertEqual(patch_res.data['first_name'], 'Updated')
        self.assertEqual(patch_res.data['profile']['role'], self.role.pk)

    def test_me_role_requires_workspace(self):
        res = self.client.patch(
            '/api/v1/users/me/',
            {'role': self.role.pk, 'workspace': None},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(res.status_code, 400)

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import TeamMember, Workspace
from .models import Profile

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class ProfileModelTest(TestCase):
    def test_profile_creation(self):
        user = User.objects.create(username="testuser")
        org = Organization.objects.create(name="Org")
        profile = Profile.objects.create(user=user, organization=org)
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.organization, org)


class UserProfileApiTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1@example.com', email='u1@example.com', password='x')
        self.other = User.objects.create_user(username='u2@example.com', email='u2@example.com', password='x')
        self.third = User.objects.create_user(username='u3@example.com', email='u3@example.com', password='x')
        self.org = Organization.objects.create(name='Users Org')
        self.other_org = Organization.objects.create(name='Other Org')
        self.ws = Workspace.objects.create(name='Users WS', organization=self.org)
        OrganizationMember.objects.create(organization=self.org, user=self.user, role=OrganizationMember.MEMBER)
        OrganizationMember.objects.create(organization=self.org, user=self.other, role=OrganizationMember.MEMBER)
        OrganizationMember.objects.create(organization=self.other_org, user=self.third, role=OrganizationMember.MEMBER)
        TeamMember.objects.create(workspace=self.ws, user=self.user, role=TeamMember.MEMBER)
        TeamMember.objects.create(workspace=self.ws, user=self.other, role=TeamMember.MEMBER)

    def test_organization_scoped_user_listing(self):
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
            {'first_name': 'Updated', 'bio': 'Developer', 'organization': self.org.pk},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(patch_res.status_code, 200, patch_res.data)
        self.assertEqual(patch_res.data['first_name'], 'Updated')

    def test_me_rejects_inaccessible_organization(self):
        res = self.client.patch(
            '/api/v1/users/me/',
            {'organization': self.other_org.pk},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(res.status_code, 400)

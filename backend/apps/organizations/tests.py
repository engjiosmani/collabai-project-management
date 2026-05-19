from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Organization, OrganizationMember

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class OrganizationModelTest(TestCase):
    def test_create_organization(self):
        org = Organization.objects.create(name="Test Org")
        self.assertEqual(org.name, "Test Org")


class OrganizationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='org@example.com', email='org@example.com', password='x')
        self.org = Organization.objects.create(name='Alpha Org', description='Primary')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.ADMIN,
        )

    def test_auth_required(self):
        res = self.client.get('/api/v1/organizations/')
        self.assertEqual(res.status_code, 401)

    def test_crud(self):
        res = self.client.post(
            '/api/v1/organizations/',
            {'name': 'Beta Org', 'description': 'B'},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(res.status_code, 201, res.data)
        oid = res.data['id']

        res = self.client.get('/api/v1/organizations/?search=alpha', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 200)
        names = [item['name'] for item in res.data.get('results', res.data)]
        self.assertIn('Alpha Org', names)

        res = self.client.patch(
            f'/api/v1/organizations/{oid}/',
            {'description': 'Updated'},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['description'], 'Updated')

        res = self.client.delete(f'/api/v1/organizations/{oid}/', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 204)

    def test_ordering(self):
        Organization.objects.create(name='Zulu Org')
        res = self.client.get('/api/v1/organizations/?ordering=-name', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 200)
        names = [item['name'] for item in res.data.get('results', res.data)]
        self.assertGreaterEqual(names[0], names[-1])


from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import TeamMember, Workspace
from django.core.cache import cache

from common.cache import NAMESPACE_WORKSPACES, make_list_key


def _jwt_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'workspaces-cache-tests',
    },
})
class WorkspaceListCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='wscache@example.com',
            email='wscache@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='WS Cache Org')
        self.workspace = Workspace.objects.create(name='Cached WS', organization=self.org)
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=TeamMember.WORKSPACE_ADMIN,
        )
        self.client = APIClient()
        self.client.credentials(**_jwt_header(self.user))

    def test_workspace_list_is_cached(self):
        with CaptureQueriesContext(connection) as first_ctx:
            first = self.client.get('/api/v1/workspaces/')
        self.assertEqual(first.status_code, 200)
        with CaptureQueriesContext(connection) as second_ctx:
            second = self.client.get('/api/v1/workspaces/')
        self.assertEqual(second.status_code, 200)
        self.assertLess(len(second_ctx.captured_queries), len(first_ctx.captured_queries))

    def test_workspace_rename_invalidates_cache(self):
        self.client.get('/api/v1/workspaces/')
        self.client.patch(
            f'/api/v1/workspaces/{self.workspace.pk}/',
            {'name': 'Renamed WS'},
            format='json',
        )
        after = self.client.get('/api/v1/workspaces/')
        names = [w['name'] for w in after.data.get('results', after.data)]
        self.assertIn('Renamed WS', names)

    def test_distinct_cache_keys_per_user(self):
        other = get_user_model().objects.create_user(
            username='wsother@example.com',
            email='wsother@example.com',
            password='StrongPass123!',
        )
        other_org = Organization.objects.create(name='Other WS Cache Org')
        OrganizationMember.objects.create(
            organization=other_org,
            user=other,
            role=OrganizationMember.MEMBER,
        )
        self.client.get('/api/v1/workspaces/')
        APIClient().get('/api/v1/workspaces/', **_jwt_header(other))
        key_a = make_list_key(NAMESPACE_WORKSPACES, self.user.pk, '/api/v1/workspaces/')
        key_b = make_list_key(NAMESPACE_WORKSPACES, other.pk, '/api/v1/workspaces/')
        self.assertNotEqual(key_a, key_b)

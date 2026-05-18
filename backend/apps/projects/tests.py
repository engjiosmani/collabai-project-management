from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.workspaces.models import TeamMember

from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from common.cache import make_list_key
from .models import Project, ProjectMember, Subscription, Integration
from .views import CACHE_NAMESPACE

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class ProjectModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="projectuser", password="test12345")
        self.org = Organization.objects.create(name="Test Organization")
        self.workspace = Workspace.objects.create(name="Test Workspace", organization=self.org)

    def test_create_project(self):
        project = Project.objects.create(
            workspace=self.workspace,
            name="CollabAI Project",
            description="Project management system"
        )

        self.assertEqual(project.workspace, self.workspace)
        self.assertEqual(project.name, "CollabAI Project")

    def test_create_project_member(self):
        project = Project.objects.create(workspace=self.workspace, name="Project A")
        member = ProjectMember.objects.create(project=project, user=self.user)

        self.assertEqual(member.project, project)
        self.assertEqual(member.user, self.user)

    def test_create_subscription(self):
        subscription = Subscription.objects.create(
            workspace=self.workspace,
            plan_name="Free"
        )

        self.assertEqual(subscription.workspace, self.workspace)
        self.assertTrue(subscription.is_active)

    def test_create_integration(self):
        integration = Integration.objects.create(
            workspace=self.workspace,
            name="GitHub",
            provider="github"
        )

        self.assertEqual(integration.workspace, self.workspace)
        self.assertEqual(integration.provider, "github")


class ProjectCRUDAPITest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mem@example.com', email='mem@example.com',
                                               password='x')
        self.outsider = User.objects.create_user(username='out@example.com', email='out@example.com',
                                                 password='x')
        self.org = Organization.objects.create(name='API Org')
        self.workspace = Workspace.objects.create(name='API WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.member)
        self.project = Project.objects.create(workspace=self.workspace, name='Seed Project')

    def test_list_requires_authentication(self):
        res = self.client.get('/api/v1/projects/')
        self.assertEqual(res.status_code, 401)

    def test_member_can_list_and_retrieve(self):
        res = self.client.get('/api/v1/projects/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data.get('results', res.data)), 1)

        res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'Seed Project')

    def test_outsider_cannot_see_foreign_project(self):
        res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(self.outsider))
        self.assertEqual(res.status_code, 404)

    def test_member_can_create_update_delete(self):
        create = self.client.post(
            '/api/v1/projects/',
            {
                'workspace': self.workspace.pk,
                'name': 'New API Project',
                'description': 'd',
                'is_active': True,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(create.status_code, 201, create.data)
        pid = create.data['id']

        patch = self.client.patch(
            f'/api/v1/projects/{pid}/',
            {'description': 'updated'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.data['description'], 'updated')

        delete = self.client.delete(f'/api/v1/projects/{pid}/', **_jwt_header(self.member))
        self.assertEqual(delete.status_code, 204)

    def test_duplicate_name_per_workspace_returns_400(self):
        res = self.client.post(
            '/api/v1/projects/',
            {'workspace': self.workspace.pk, 'name': 'Seed Project'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 400)

    def test_outsider_cannot_create_in_workspace(self):
        res = self.client.post(
            '/api/v1/projects/',
            {'workspace': self.workspace.pk, 'name': 'Hack'},
            format='json',
            **_jwt_header(self.outsider),
        )
        self.assertEqual(res.status_code, 400)

    def test_list_supports_pagination_filter_search_ordering(self):
        Project.objects.create(workspace=self.workspace, name='Alpha Search', is_active=True)
        Project.objects.create(workspace=self.workspace, name='Zulu Search', is_active=False)

        res = self.client.get(
            '/api/v1/projects/?is_active=true&search=search&ordering=name&page_size=1',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['name'], 'Alpha Search')


class ProjectLoginJWTAuthTest(APITestCase):
    """Ensures real JWT from login works with project endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(username='jwt@example.com', email='jwt@example.com',
                                             password='SecretPass123!')
        self.org = Organization.objects.create(name='JWT Org')
        self.ws = Workspace.objects.create(name='JWT WS', organization=self.org)
        TeamMember.objects.create(workspace=self.ws, user=self.user)

    def test_login_then_access_projects(self):
        login = self.client.post(
            '/api/v1/auth/login',
            {'email': 'jwt@example.com', 'password': 'SecretPass123!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)
        token = login.data['access']
        res = self.client.get('/api/v1/projects/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)


@override_settings(CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'projects-cache-tests',
}})
class ProjectListCacheTest(APITestCase):
    """Verifies that GET /api/v1/projects/ is cached and invalidated on writes."""

    def setUp(self):
        cache.clear()
        self.member = User.objects.create_user(
            username='cachemem@example.com', email='cachemem@example.com', password='x',
        )
        self.other = User.objects.create_user(
            username='cacheother@example.com', email='cacheother@example.com', password='x',
        )
        self.org = Organization.objects.create(name='Cache Org')
        self.workspace = Workspace.objects.create(name='Cache WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.member)
        TeamMember.objects.create(workspace=self.workspace, user=self.other)
        Project.objects.create(workspace=self.workspace, name='Seed Cached Project')

    def _list(self, user):
        return self.client.get('/api/v1/projects/', **_jwt_header(user))

    def test_second_list_call_serves_from_cache(self):
        with CaptureQueriesContext(connection) as first_ctx:
            first = self._list(self.member)
        self.assertEqual(first.status_code, 200)

        with CaptureQueriesContext(connection) as second_ctx:
            second = self._list(self.member)
        self.assertEqual(second.status_code, 200)

        self.assertLess(
            len(second_ctx.captured_queries),
            len(first_ctx.captured_queries),
            'Cached list call should issue strictly fewer DB queries than the first call',
        )

    def test_create_invalidates_cache(self):
        self._list(self.member)
        res = self.client.post(
            '/api/v1/projects/',
            {'workspace': self.workspace.pk, 'name': 'Brand New Project'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)

        after = self._list(self.member)
        names = [p['name'] for p in after.data.get('results', after.data)]
        self.assertIn('Brand New Project', names)

    def test_update_invalidates_cache(self):
        target = Project.objects.create(workspace=self.workspace, name='Original Name')
        self._list(self.member)

        res = self.client.patch(
            f'/api/v1/projects/{target.pk}/',
            {'name': 'Renamed Project'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200, res.data)

        after = self._list(self.member)
        names = [p['name'] for p in after.data.get('results', after.data)]
        self.assertIn('Renamed Project', names)
        self.assertNotIn('Original Name', names)

    def test_delete_invalidates_cache(self):
        target = Project.objects.create(workspace=self.workspace, name='To Delete')
        self._list(self.member)

        res = self.client.delete(f'/api/v1/projects/{target.pk}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 204)

        after = self._list(self.member)
        names = [p['name'] for p in after.data.get('results', after.data)]
        self.assertNotIn('To Delete', names)

    def test_users_have_distinct_cache_keys(self):
        self._list(self.member)
        self._list(self.other)

        member_key = make_list_key(CACHE_NAMESPACE, self.member.pk, '/api/v1/projects/')
        other_key = make_list_key(CACHE_NAMESPACE, self.other.pk, '/api/v1/projects/')
        self.assertNotEqual(member_key, other_key)
        self.assertIsNotNone(cache.get(member_key))
        self.assertIsNotNone(cache.get(other_key))
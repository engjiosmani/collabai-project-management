from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import TeamMember, Workspace

from common.cache import NAMESPACE_PROJECTS, make_list_key
from .models import Project, ProjectMember, Subscription, Integration

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class ProjectModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="projectuser", password="test12345")
        self.org = Organization.objects.create(name="Test Organization")

    def test_create_project(self):
        project = Project.objects.create(
            organization=self.org,
            name="CollabAI Project",
            description="Project management system",
        )
        self.assertEqual(project.organization, self.org)
        self.assertEqual(project.name, "CollabAI Project")

    def test_create_project_member(self):
        project = Project.objects.create(organization=self.org, name="Project A")
        member = ProjectMember.objects.create(project=project, user=self.user)
        self.assertEqual(member.project, project)
        self.assertEqual(member.user, self.user)

    def test_create_subscription(self):
        subscription = Subscription.objects.create(
            organization=self.org,
            plan_name="Free",
        )
        self.assertEqual(subscription.organization, self.org)
        self.assertTrue(subscription.is_active)

    def test_create_integration(self):
        integration = Integration.objects.create(
            organization=self.org,
            name="Calendar",
            provider="calendar",
        )
        self.assertEqual(integration.organization, self.org)
        self.assertEqual(integration.provider, "calendar")


class ProjectCRUDAPITest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='proj_admin@example.com',
            email='proj_admin@example.com',
            password='x',
        )
        self.member = User.objects.create_user(
            username='proj_member@example.com',
            email='proj_member@example.com',
            password='x',
        )
        self.outsider = User.objects.create_user(
            username='proj_outsider@example.com',
            email='proj_outsider@example.com',
            password='x',
        )

        self.org = Organization.objects.create(name='CRUD Org')

        OrganizationMember.objects.create(
            organization=self.org,
            user=self.member,
            role=OrganizationMember.MEMBER,
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.admin_user,
            role=OrganizationMember.ORG_ADMIN,
        )
        self.workspace = Workspace.objects.create(
            organization=self.org,
            name='CRUD Workspace',
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=TeamMember.MANAGER,
        )

        self.project = Project.objects.create(
            organization=self.org,
            workspace=self.workspace,
            name='Seed Project',
        )

    def test_member_cannot_delete_project(self):
        response = self.client.delete(
            f'/api/v1/projects/{self.project.pk}/',
            **_jwt_header(self.member),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_project(self):
        response = self.client.delete(
            f'/api/v1/projects/{self.project.pk}/',
            **_jwt_header(self.admin_user),
        )
        self.assertEqual(response.status_code, 204)

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
                'organization': self.org.pk,
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

        delete = self.client.delete(f'/api/v1/projects/{pid}/', **_jwt_header(self.admin_user))
        self.assertEqual(delete.status_code, 204)

    def test_duplicate_name_per_organization_returns_400(self):
        res = self.client.post(
            '/api/v1/projects/',
            {'organization': self.org.pk, 'workspace': self.workspace.pk, 'name': 'Seed Project'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 400)

    def test_create_rejects_past_start_date(self):
        yesterday = timezone.localdate() - timedelta(days=1)

        res = self.client.post(
            '/api/v1/projects/',
            {
                'organization': self.org.pk,
                'workspace': self.workspace.pk,
                'name': 'Past Start Project',
                'start_date': yesterday.isoformat(),
            },
            format='json',
            **_jwt_header(self.member),
        )

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['start_date'][0], 'Start date cannot be in the past.')

    def test_create_rejects_past_due_date(self):
        yesterday = timezone.localdate() - timedelta(days=1)

        res = self.client.post(
            '/api/v1/projects/',
            {
                'organization': self.org.pk,
                'workspace': self.workspace.pk,
                'name': 'Past Due Project',
                'due_date': yesterday.isoformat(),
            },
            format='json',
            **_jwt_header(self.member),
        )

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['due_date'][0], 'Due date cannot be in the past.')

    def test_create_rejects_due_date_before_start_date(self):
        today = timezone.localdate()

        res = self.client.post(
            '/api/v1/projects/',
            {
                'organization': self.org.pk,
                'workspace': self.workspace.pk,
                'name': 'Invalid Date Range Project',
                'start_date': (today + timedelta(days=3)).isoformat(),
                'due_date': (today + timedelta(days=1)).isoformat(),
            },
            format='json',
            **_jwt_header(self.member),
        )

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['due_date'][0], 'Due date cannot be earlier than start date.')

    def test_outsider_cannot_create_in_organization(self):
        res = self.client.post(
            '/api/v1/projects/',
            {'organization': self.org.pk, 'workspace': self.workspace.pk, 'name': 'Hack'},
            format='json',
            **_jwt_header(self.outsider),
        )
        self.assertEqual(res.status_code, 400)

    def test_list_supports_pagination_filter_search_ordering(self):
        Project.objects.create(organization=self.org, workspace=self.workspace, name='Alpha Search', is_active=True)
        Project.objects.create(organization=self.org, workspace=self.workspace, name='Zulu Search', is_active=False)

        res = self.client.get(
            '/api/v1/projects/?is_active=true&search=search&ordering=name&page_size=1',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['name'], 'Alpha Search')

    def test_search_matches_organization_name(self):
        res = self.client.get(
            f'/api/v1/projects/?organization={self.org.pk}&search=crud&ordering=name&page_size=1',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['name'], 'Seed Project')

    def test_invalid_query_parameter_returns_400(self):
        res = self.client.get('/api/v1/projects/?organization=abc', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 400)

    def test_outsider_does_not_see_foreign_projects_in_list(self):
        res = self.client.get('/api/v1/projects/', **_jwt_header(self.outsider))
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 0)

    def test_regular_member_needs_project_membership_to_see_project(self):
        regular = User.objects.create_user(
            username='regular@example.com',
            email='regular@example.com',
            password='x',
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=regular,
            role=OrganizationMember.MEMBER,
        )

        res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(regular))
        self.assertEqual(res.status_code, 404)

        ProjectMember.objects.create(project=self.project, user=regular)
        res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(regular))
        self.assertEqual(res.status_code, 200)


class ProjectLoginJWTAuthTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='jwt@example.com',
            email='jwt@example.com',
            password='SecretPass123!',
        )
        self.org = Organization.objects.create(name='JWT Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )

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
    def setUp(self):
        cache.clear()
        self.member = User.objects.create_user(
            username='cachemem@example.com', email='cachemem@example.com', password='x',
        )
        self.other = User.objects.create_user(
            username='cacheother@example.com', email='cacheother@example.com', password='x',
        )
        self.org = Organization.objects.create(name='Cache Org')

        OrganizationMember.objects.create(
            organization=self.org,
            user=self.member,
            role=OrganizationMember.ORG_ADMIN,
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.other,
            role=OrganizationMember.MEMBER,
        )
        self.workspace = Workspace.objects.create(organization=self.org, name='Cache Workspace')

        Project.objects.create(organization=self.org, workspace=self.workspace, name='Seed Cached Project')

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
        )

    def test_create_invalidates_cache(self):
        self._list(self.member)
        res = self.client.post(
            '/api/v1/projects/',
            {'organization': self.org.pk, 'workspace': self.workspace.pk, 'name': 'Brand New Project'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)

        after = self._list(self.member)
        names = [p['name'] for p in after.data.get('results', after.data)]
        self.assertIn('Brand New Project', names)

    def test_update_invalidates_cache(self):
        target = Project.objects.create(organization=self.org, workspace=self.workspace, name='Original Name')
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
        target = Project.objects.create(organization=self.org, workspace=self.workspace, name='To Delete')
        self._list(self.member)

        res = self.client.delete(f'/api/v1/projects/{target.pk}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 204)

        after = self._list(self.member)
        names = [p['name'] for p in after.data.get('results', after.data)]
        self.assertNotIn('To Delete', names)

    def test_users_have_distinct_cache_keys(self):
        self._list(self.member)
        self._list(self.other)

        member_key = make_list_key(NAMESPACE_PROJECTS, self.member.pk, '/api/v1/projects/')
        other_key = make_list_key(NAMESPACE_PROJECTS, self.other.pk, '/api/v1/projects/')
        self.assertNotEqual(member_key, other_key)
        self.assertIsNotNone(cache.get(member_key))
        self.assertIsNotNone(cache.get(other_key))

class ProjectTenantIsolationAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='tenant-admin@example.com', email='tenant-admin@example.com', password='x')
        self.outsider = User.objects.create_user(username='tenant-outsider@example.com', email='tenant-outsider@example.com', password='x')
        self.org = Organization.objects.create(name='Tenant Project Org A')
        self.other_org = Organization.objects.create(name='Tenant Project Org B')
        OrganizationMember.objects.create(organization=self.org, user=self.admin, role=OrganizationMember.ORG_ADMIN)
        OrganizationMember.objects.create(organization=self.other_org, user=self.outsider, role=OrganizationMember.MEMBER)
        self.project = Project.objects.create(organization=self.org, name='Scoped Project')

    def test_cannot_add_user_from_another_organization_to_project(self):
        response = self.client.post(
            f'/api/v1/projects/{self.project.pk}/members/',
            {'user_id': self.outsider.pk},
            format='json',
            **_jwt_header(self.admin),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.outsider).exists())

    def test_active_organization_header_scopes_project_list(self):
        second_org = Organization.objects.create(name='Tenant Project Org C')
        OrganizationMember.objects.create(organization=second_org, user=self.admin, role=OrganizationMember.ORG_ADMIN)
        Project.objects.create(organization=second_org, name='Other Scoped Project')

        response = self.client.get(
            '/api/v1/projects/',
            HTTP_X_ORGANIZATION_ID=str(self.org.pk),
            **_jwt_header(self.admin),
        )
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.data.get('results', response.data)]
        self.assertIn('Scoped Project', names)
        self.assertNotIn('Other Scoped Project', names)

    def test_invalid_active_organization_header_returns_no_project_data(self):
        response = self.client.get(
            '/api/v1/projects/',
            HTTP_X_ORGANIZATION_ID=str(self.other_org.pk),
            **_jwt_header(self.admin),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('results', response.data), [])

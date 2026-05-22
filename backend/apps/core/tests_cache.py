from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import TeamMember, Workspace
from common.cache import NAMESPACE_DASHBOARD, bump_version, get_version, make_list_key


def _jwt_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cache-helper-unit',
    },
})
class CacheVersionHelperTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_bump_version_increments_namespace(self):
        self.assertEqual(get_version(NAMESPACE_DASHBOARD), 1)
        bump_version(NAMESPACE_DASHBOARD)
        self.assertEqual(get_version(NAMESPACE_DASHBOARD), 2)

    def test_list_key_changes_after_bump(self):
        first = make_list_key(NAMESPACE_DASHBOARD, 7, '/api/v1/dashboard/summary/')
        bump_version(NAMESPACE_DASHBOARD)
        second = make_list_key(NAMESPACE_DASHBOARD, 7, '/api/v1/dashboard/summary/')
        self.assertNotEqual(first, second)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'dashboard-cache-tests',
        },
    },
    RAG_AUTO_INDEX=False,
)
class DashboardSummaryCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='dash@example.com',
            email='dash@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='Dash Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )
        workspace = Workspace.objects.create(organization=self.org, name='Dash WS')
        TeamMember.objects.create(
            workspace=workspace,
            user=self.user,
            role=TeamMember.MANAGER,
        )
        self.client = APIClient()
        self.client.credentials(**_jwt_header(self.user))

    def test_dashboard_second_get_uses_cache(self):
        url = '/api/v1/dashboard/summary/'
        with CaptureQueriesContext(connection) as first_ctx:
            first = self.client.get(url)
        self.assertEqual(first.status_code, 200)

        with CaptureQueriesContext(connection) as second_ctx:
            second = self.client.get(url)
        self.assertEqual(second.status_code, 200)
        self.assertLess(len(second_ctx.captured_queries), len(first_ctx.captured_queries))

    def test_task_create_invalidates_dashboard_cache(self):
        url = '/api/v1/dashboard/summary/'
        self.client.get(url)
        project = Project.objects.create(organization=self.org, name='P')
        status_obj = TaskStatus.objects.create(name='Open')
        priority = TaskPriority.objects.create(name='High', level=1)
        created = self.client.post(
            '/api/v1/tasks/',
            {
                'project': project.pk,
                'title': 'New cached task',
                'status': status_obj.pk,
                'priority': priority.pk,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        after = self.client.get(url)
        self.assertEqual(after.data['total_tasks'], 1)

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import Role, TeamMember, Workspace


def _jwt(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'comments-cache-tests',
        },
    },
    RAG_AUTO_INDEX=False,
)
class CommentListCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='cmtcache@example.com',
            email='cmtcache@example.com',
            password='x',
        )
        org = Organization.objects.create(name='C Org')
        ws = Workspace.objects.create(name='C WS', organization=org)
        role = Role.objects.create(workspace=ws, name=Role.MEMBER)
        TeamMember.objects.create(workspace=ws, user=self.user, role=role)
        project = Project.objects.create(workspace=ws, name='P')
        status = TaskStatus.objects.create(name='Open')
        priority = TaskPriority.objects.create(name='H', level=1)
        self.task = Task.objects.create(
            project=project,
            title='T',
            status=status,
            priority=priority,
        )
        self.client = APIClient()

    def test_comment_list_cached(self):
        url = '/api/v1/comments/'
        with CaptureQueriesContext(connection) as first:
            self.client.get(url, **_jwt(self.user))
        with CaptureQueriesContext(connection) as second:
            self.client.get(url, **_jwt(self.user))
        self.assertLess(len(second.captured_queries), len(first.captured_queries))

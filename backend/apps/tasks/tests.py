from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.organizations.models import Organization
from apps.workspaces.models import (TeamMember,Workspace,Role)
from apps.projects.models import Project
from common.cache import make_list_key
from .models import Task, TaskStatus, TaskPriority, Label, TaskLabel, Attachment
from .views import CACHE_NAMESPACE

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}

class TaskModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="taskuser", password="test12345")
        self.org = Organization.objects.create(name="Task Org")
        self.workspace = Workspace.objects.create(name="Task Workspace", organization=self.org)
        self.project = Project.objects.create(workspace=self.workspace, name="Task Project")
        self.status, _ = TaskStatus.objects.get_or_create(name="To Do")
        self.priority = TaskPriority.objects.create(name="High", level=1)

    def test_create_task(self):
        task = Task.objects.create(
            project=self.project,
            title="Create database models",
            status=self.status,
            priority=self.priority,
            assigned_to=self.user
        )

        self.assertEqual(task.project, self.project)
        self.assertEqual(task.status, self.status)
        self.assertEqual(task.priority, self.priority)
        self.assertEqual(task.assigned_to, self.user)

    def test_create_label_and_task_label(self):
        task = Task.objects.create(
            project=self.project,
            title="Task with label",
            status=self.status,
            priority=self.priority
        )
        label = Label.objects.create(name="Backend", color="#000000")
        task_label = TaskLabel.objects.create(task=task, label=label)

        self.assertEqual(task_label.task, task)
        self.assertEqual(task_label.label, label)

    def test_create_attachment(self):
        task = Task.objects.create(
            project=self.project,
            title="Task with attachment",
            status=self.status,
            priority=self.priority
        )

        attachment = Attachment.objects.create(
            task=task,
            uploaded_by=self.user,
            file="attachments/test.txt",
            file_name="test.txt"
        )

        self.assertEqual(attachment.task, task)
        self.assertEqual(attachment.uploaded_by, self.user)
        self.assertEqual(attachment.file_name, "test.txt")

class TaskCRUDAPITest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='taskmem@example.com', email='taskmem@example.com', password='x')
        self.assignee = User.objects.create_user(username='assign@example.com', email='assign@example.com', password='x')
        self.outsider = User.objects.create_user(username='taskout@example.com', email='taskout@example.com', password='x')
        self.org = Organization.objects.create(name='Task API Org')
        self.workspace = Workspace.objects.create(name='Task API WS', organization=self.org)
        self.manager_role = Role.objects.create(
            workspace=self.workspace,
            name=Role.MANAGER
        )

        self.member_role = Role.objects.create(
            workspace=self.workspace,
            name=Role.MEMBER
        )

        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=self.manager_role
        )

        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.assignee,
            role=self.member_role
        )
        self.project = Project.objects.create(workspace=self.workspace, name='Task API Project')
        self.status, _ = TaskStatus.objects.get_or_create(name='Open')
        self.priority = TaskPriority.objects.create(name='P1', level=1)
        self.task = Task.objects.create(
            project=self.project,
            title='Seed Task',
            status=self.status,
            priority=self.priority,
        )

    def test_unauthenticated_denied(self):
        self.assertEqual(self.client.get('/api/v1/tasks/').status_code, 401)

    def test_crud_for_workspace_member(self):
        res = self.client.get('/api/v1/tasks/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)

        res = self.client.post(
            '/api/v1/tasks/',
            {
                'project': self.project.pk,
                'title': 'New Task',
                'status': self.status.pk,
                'priority': self.priority.pk,
                'assigned_to': self.assignee.pk,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status_name'], self.status.name)
        self.assertEqual(res.data['priority_name'], self.priority.name)
        self.assertEqual(res.data['assigned_to_email'], self.assignee.email)
        tid = res.data['id']

        res = self.client.patch(
            f'/api/v1/tasks/{tid}/',
            {'title': 'Renamed'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['title'], 'Renamed')

        res = self.client.delete(f'/api/v1/tasks/{tid}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 204)

    def test_assignee_must_be_workspace_member(self):
        res = self.client.post(
            '/api/v1/tasks/',
            {
                'project': self.project.pk,
                'title': 'Bad assign',
                'assigned_to': self.outsider.pk,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 400)

    def test_outsider_detail_is_404(self):
        res = self.client.get(f'/api/v1/tasks/{self.task.pk}/', **_jwt_header(self.outsider))
        self.assertEqual(res.status_code, 404)

    def test_list_supports_pagination_filter_search_ordering(self):
        progress_status, _ = TaskStatus.objects.get_or_create(name='In Progress')
        high_priority, _ = TaskPriority.objects.get_or_create(name='High', defaults={'level': 2})

        Task.objects.create(
            project=self.project,
            title='Alpha Task Search',
            status=progress_status,
            priority=high_priority,
            assigned_to=self.assignee,
        )
        Task.objects.create(
            project=self.project,
            title='Zulu Task Search',
            status=progress_status,
            priority=high_priority,
            assigned_to=self.assignee,
        )

        res = self.client.get(
            (
                f'/api/v1/tasks/?project={self.project.pk}'
                f'&workspace={self.workspace.pk}'
                f'&organization={self.org.pk}'
                f'&status=in_progress'
                f'&priority=high'
                f'&assignee={self.assignee.pk}'
                f'&search=search&ordering=title&page_size=1'
            ),
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['title'], 'Alpha Task Search')

    def test_search_matches_labels_and_deduplicates_results(self):
        task = Task.objects.create(
            project=self.project,
            title='Label Search Task',
            status=self.status,
            priority=self.priority,
            assigned_to=self.assignee,
        )
        frontend_label = Label.objects.create(name='Frontend', color='#000000')
        frontend_docs_label = Label.objects.create(name='Frontend Docs', color='#111111')
        TaskLabel.objects.create(task=task, label=frontend_label)
        TaskLabel.objects.create(task=task, label=frontend_docs_label)

        res = self.client.get(
            f'/api/v1/tasks/?search=frontend&page_size=10&ordering=created_at',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['title'], 'Label Search Task')

    def test_invalid_query_parameter_returns_400(self):
        res = self.client.get(
            f'/api/v1/tasks/?workspace=abc',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 400)


class TaskStatusAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='status@example.com', email='status@example.com', password='x')
        TaskStatus.objects.get_or_create(name='Done')
        TaskStatus.objects.get_or_create(name='In Progress')
        TaskStatus.objects.get_or_create(name='To Do')

    def test_authenticated_user_can_list_statuses(self):
        res = self.client.get('/api/v1/task-statuses/', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 200)

        data = res.data.get('results', res.data)
        self.assertEqual([item['name'] for item in data], ['Done', 'In Progress', 'To Do'])


class TaskPermissionsAPITest(APITestCase):
    """Workspace membership gates task access through queryset + object permission."""

    def setUp(self):
        self.user = User.objects.create_user(username='tp@example.com', email='tp@example.com', password='x')
        self.org = Organization.objects.create(name='TP Org')
        self.ws = Workspace.objects.create(name='TP WS', organization=self.org)
        self.manager_role = Role.objects.create(
            workspace=self.ws,
            name=Role.MANAGER
        )

        TeamMember.objects.create(
            workspace=self.ws,
            user=self.user,
            role=self.manager_role
        )
        self.project = Project.objects.create(workspace=self.ws, name='TP')
        self.status, _ = TaskStatus.objects.get_or_create(name='Open')
        self.task = Task.objects.create(project=self.project, title='T', status=self.status)

    def test_manager_has_object_permission_for_mutations(self):
        self.client.delete(f'/api/v1/tasks/{self.task.pk}/', **_jwt_header(self.user))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())


@override_settings(CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'tasks-cache-tests',
}})
class TaskListCacheTest(APITestCase):
    """Verifies that GET /api/v1/tasks/ is cached and invalidated on writes."""

    def setUp(self):
        cache.clear()
        self.member = User.objects.create_user(
            username='taskcache@example.com', email='taskcache@example.com', password='x',
        )
        self.other = User.objects.create_user(
            username='taskother@example.com', email='taskother@example.com', password='x',
        )
        self.org = Organization.objects.create(name='Task Cache Org')
        self.workspace = Workspace.objects.create(name='Task Cache WS', organization=self.org)
        self.manager_role = Role.objects.create(
            workspace=self.workspace,
            name=Role.MANAGER
        )

        self.member_role = Role.objects.create(
            workspace=self.workspace,
            name=Role.MEMBER
        )

        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=self.manager_role
        )

        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.other,
            role=self.member_role
        )
        self.project = Project.objects.create(workspace=self.workspace, name='Cache Project')
        self.status, _ = TaskStatus.objects.get_or_create(name='Open')
        self.priority = TaskPriority.objects.create(name='P1', level=1)
        Task.objects.create(
            project=self.project, title='Seed Cached Task',
            status=self.status, priority=self.priority,
        )

    def _list(self, user):
        return self.client.get('/api/v1/tasks/', **_jwt_header(user))

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
            '/api/v1/tasks/',
            {
                'project': self.project.pk,
                'title': 'Brand New Task',
                'status': self.status.pk,
                'priority': self.priority.pk,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)

        after = self._list(self.member)
        titles = [t['title'] for t in after.data.get('results', after.data)]
        self.assertIn('Brand New Task', titles)

    def test_update_invalidates_cache(self):
        target = Task.objects.create(
            project=self.project, title='Original Title',
            status=self.status, priority=self.priority,
        )
        self._list(self.member)

        res = self.client.patch(
            f'/api/v1/tasks/{target.pk}/',
            {'title': 'Renamed Task'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200, res.data)

        after = self._list(self.member)
        titles = [t['title'] for t in after.data.get('results', after.data)]
        self.assertIn('Renamed Task', titles)
        self.assertNotIn('Original Title', titles)

    def test_delete_invalidates_cache(self):
        target = Task.objects.create(
            project=self.project, title='To Delete',
            status=self.status, priority=self.priority,
        )
        self._list(self.member)

        res = self.client.delete(f'/api/v1/tasks/{target.pk}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 204)

        after = self._list(self.member)
        titles = [t['title'] for t in after.data.get('results', after.data)]
        self.assertNotIn('To Delete', titles)

    def test_users_have_distinct_cache_keys(self):
        self._list(self.member)
        self._list(self.other)

        member_key = make_list_key(CACHE_NAMESPACE, self.member.pk, '/api/v1/tasks/')
        other_key = make_list_key(CACHE_NAMESPACE, self.other.pk, '/api/v1/tasks/')
        self.assertNotEqual(member_key, other_key)
        self.assertIsNotNone(cache.get(member_key))
        self.assertIsNotNone(cache.get(other_key))
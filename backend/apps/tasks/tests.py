from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project, ProjectMember
from apps.workspaces.models import TeamMember, Workspace
from common.cache import NAMESPACE_TASKS, make_list_key
from apps.comments.models import ActivityLog
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Task, TaskStatus, TaskPriority, Label, TaskLabel, Attachment
from .status_utils import completed_task_status_ids, is_completed_status_name

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}

class TaskModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="taskuser", password="test12345")
        self.org = Organization.objects.create(name="Task Org")
        self.project = Project.objects.create(organization=self.org, name="Task Project")
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
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.member,
            role=OrganizationMember.MEMBER,
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.assignee,
            role=OrganizationMember.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            organization=self.org,
            name='Task API Workspace',
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=TeamMember.MANAGER,
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.assignee,
            role=TeamMember.MEMBER,
        )
        self.project = Project.objects.create(
            organization=self.org,
            workspace=self.workspace,
            name='Task API Project',
        )
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
                'labels': ['Frontend', 'Urgent'],
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status_name'], self.status.name)
        self.assertEqual(res.data['priority_name'], self.priority.name)
        self.assertEqual(res.data['assigned_to_email'], self.assignee.email)
        self.assertEqual([label['name'] for label in res.data['labels']], ['Frontend', 'Urgent'])
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

    def test_creator_can_delete_after_role_changes(self):
        res = self.client.post(
            '/api/v1/tasks/',
            {
                'project': self.project.pk,
                'title': 'Creator Delete Task',
                'status': self.status.pk,
                'priority': self.priority.pk,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)
        tid = res.data['id']
        TeamMember.objects.filter(workspace=self.workspace, user=self.member).update(role=TeamMember.MEMBER)

        res = self.client.delete(f'/api/v1/tasks/{tid}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 204, res.data)

    def test_attachment_upload_and_list(self):
        task = Task.objects.create(
            project=self.project,
            title='Attachment Task',
            status=self.status,
            priority=self.priority,
            assigned_to=self.member,
        )

        upload = SimpleUploadedFile('plan.txt', b'hello world', content_type='text/plain')
        res = self.client.post(
            f'/api/v1/tasks/{task.pk}/attachments/',
            {'file': upload},
            format='multipart',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['file_name'], 'plan.txt')

        res = self.client.get(f'/api/v1/tasks/{task.pk}/attachments/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

        attachment_id = res.data[0]['id']
        download = self.client.get(
            f'/api/v1/tasks/{task.pk}/attachments/{attachment_id}/download/',
            **_jwt_header(self.member),
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment; filename="plan.txt"', download.headers.get('Content-Disposition', ''))
        self.assertEqual(b''.join(download.streaming_content), b'hello world')

        delete_res = self.client.delete(
            f'/api/v1/tasks/{task.pk}/attachments/{attachment_id}/',
            **_jwt_header(self.member),
        )
        self.assertEqual(delete_res.status_code, 204)

        res = self.client.get(f'/api/v1/tasks/{task.pk}/attachments/', **_jwt_header(self.member))
        self.assertEqual(len(res.data), 0)

    def test_task_priority_endpoint(self):
        TaskPriority.objects.all().delete()
        TaskPriority.objects.create(name='Low', level=1)
        TaskPriority.objects.create(name='High', level=3)
        res = self.client.get('/api/v1/task-priorities/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        data = res.data.get('results', res.data)
        self.assertEqual([item['name'] for item in data], ['Low', 'High'])

    def test_task_mutations_create_activity_logs(self):
        done_status, _ = TaskStatus.objects.get_or_create(name='Done')

        res = self.client.post(
            '/api/v1/tasks/',
            {
                'project': self.project.pk,
                'title': 'Activity Task',
                'status': self.status.pk,
                'priority': self.priority.pk,
            },
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 201, res.data)
        tid = res.data['id']
        self.assertTrue(
            ActivityLog.objects.filter(task_id=tid, action='Task created').exists()
        )

        res = self.client.patch(
            f'/api/v1/tasks/{tid}/',
            {'status': done_status.pk},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(
            ActivityLog.objects.filter(task_id=tid, action='Status changed').exists()
        )

        summary = self.client.get('/api/v1/dashboard/summary/', **_jwt_header(self.member))
        self.assertEqual(summary.status_code, 200)
        self.assertGreaterEqual(summary.data['total_activity_logs'], 2)
        self.assertGreaterEqual(len(summary.data['recent_activity']), 1)

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
            f'/api/v1/tasks/?organization=abc',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 400)

    def test_assigned_member_can_update_status_but_not_assign_or_delete(self):
        ProjectMember.objects.create(project=self.project, user=self.assignee)
        task = Task.objects.create(
            project=self.project,
            title='Assigned Member Task',
            status=self.status,
            priority=self.priority,
            assigned_to=self.assignee,
        )
        done_status, _ = TaskStatus.objects.get_or_create(name='Done')

        res = self.client.patch(
            f'/api/v1/tasks/{task.pk}/',
            {'status': done_status.pk},
            format='json',
            **_jwt_header(self.assignee),
        )
        self.assertEqual(res.status_code, 200, res.data)

        res = self.client.patch(
            f'/api/v1/tasks/{task.pk}/',
            {'assigned_to': self.member.pk},
            format='json',
            **_jwt_header(self.assignee),
        )
        self.assertEqual(res.status_code, 403)

        res = self.client.delete(f'/api/v1/tasks/{task.pk}/', **_jwt_header(self.assignee))
        self.assertEqual(res.status_code, 403)


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
        self.assertEqual([item['name'] for item in data], ['To Do', 'In Progress', 'Done'])


@override_settings(RAG_AUTO_INDEX=False, RAG_FORCE_MEMORY_STORE=True)
class TaskPermissionsAPITest(APITestCase):
    """Workspace membership gates task access through queryset + object permission."""

    def setUp(self):
        self.user = User.objects.create_user(username='tp@example.com', email='tp@example.com', password='x')
        self.org = Organization.objects.create(name='TP Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            organization=self.org,
            name='TP Workspace',
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=TeamMember.MANAGER,
        )
        self.project = Project.objects.create(organization=self.org, workspace=self.workspace, name='TP')
        self.status, _ = TaskStatus.objects.get_or_create(name='Open')
        self.task = Task.objects.create(project=self.project, title='T', status=self.status)

    def test_manager_has_object_permission_for_mutations(self):
        self.client.delete(f'/api/v1/tasks/{self.task.pk}/', **_jwt_header(self.user))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'tasks-cache-tests',
        }
    },
    RAG_AUTO_INDEX=False,
    RAG_FORCE_MEMORY_STORE=True,
)
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
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.member,
            role=OrganizationMember.MEMBER,
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.other,
            role=OrganizationMember.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            organization=self.org,
            name='Task Cache Workspace',
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=TeamMember.MANAGER,
        )
        self.project = Project.objects.create(
            organization=self.org,
            workspace=self.workspace,
            name='Cache Project',
        )
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

        member_key = make_list_key(NAMESPACE_TASKS, self.member.pk, '/api/v1/tasks/')
        other_key = make_list_key(NAMESPACE_TASKS, self.other.pk, '/api/v1/tasks/')
        self.assertNotEqual(member_key, other_key)
        self.assertIsNotNone(cache.get(member_key))
        self.assertIsNotNone(cache.get(other_key))


class TaskStatusUtilsTest(TestCase):
    def test_done_status_detection(self):
        done, _ = TaskStatus.objects.get_or_create(name='Done')
        todo, _ = TaskStatus.objects.get_or_create(name='To Do')
        self.assertTrue(is_completed_status_name('Done'))
        self.assertFalse(is_completed_status_name('To Do'))
        ids = completed_task_status_ids()
        self.assertIn(done.pk, ids)
        self.assertNotIn(todo.pk, ids)

class TaskTenantIsolationAPITest(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='tenant-task-a@example.com', email='tenant-task-a@example.com', password='x')
        self.user_b = User.objects.create_user(username='tenant-task-b@example.com', email='tenant-task-b@example.com', password='x')
        self.org_a = Organization.objects.create(name='Tenant Task Org A')
        self.org_b = Organization.objects.create(name='Tenant Task Org B')
        OrganizationMember.objects.create(organization=self.org_a, user=self.user_a, role=OrganizationMember.ORG_ADMIN)
        OrganizationMember.objects.create(organization=self.org_b, user=self.user_b, role=OrganizationMember.ORG_ADMIN)
        self.workspace_a = Workspace.objects.create(organization=self.org_a, name='Workspace A')
        TeamMember.objects.create(workspace=self.workspace_a, user=self.user_a, role=TeamMember.MANAGER)
        self.project_a = Project.objects.create(organization=self.org_a, name='Project A')
        self.project_b = Project.objects.create(organization=self.org_b, name='Project B')
        self.status, _ = TaskStatus.objects.get_or_create(name='Tenant Todo')
        self.priority, _ = TaskPriority.objects.get_or_create(name='Tenant Medium', level=55)
        self.task_b = Task.objects.create(project=self.project_b, title='Other Org Task', status=self.status, priority=self.priority)

    def test_delete_uses_scoped_queryset_for_guessed_cross_tenant_id(self):
        response = self.client.delete(
            f'/api/v1/tasks/{self.task_b.pk}/',
            **_jwt_header(self.user_a),
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.task_b.pk).exists())

    def test_labels_created_through_task_api_are_organization_scoped(self):
        response = self.client.post(
            '/api/v1/tasks/',
            {
                'project': self.project_a.pk,
                'title': 'Tenant Label Task',
                'status': self.status.pk,
                'priority': self.priority.pk,
                'labels': ['Backend'],
            },
            format='json',
            **_jwt_header(self.user_a),
        )
        self.assertEqual(response.status_code, 201)
        label = Label.objects.get(name='Backend', organization=self.org_a)
        self.assertTrue(TaskLabel.objects.filter(task_id=response.data['id'], label=label).exists())

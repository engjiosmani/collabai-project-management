from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.organizations.models import Organization
from apps.workspaces.models import TeamMember,Workspace
from apps.projects.models import Project
from .models import Task, TaskStatus, TaskPriority, Label, TaskLabel, Attachment

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}

class TaskModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="taskuser", password="test12345")
        self.org = Organization.objects.create(name="Task Org")
        self.workspace = Workspace.objects.create(name="Task Workspace", organization=self.org)
        self.project = Project.objects.create(workspace=self.workspace, name="Task Project")
        self.status = TaskStatus.objects.create(name="To Do")
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
        TeamMember.objects.create(workspace=self.workspace, user=self.member)
        TeamMember.objects.create(workspace=self.workspace, user=self.assignee)
        self.project = Project.objects.create(workspace=self.workspace, name='Task API Project')
        self.status = TaskStatus.objects.create(name='Open')
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


class TaskPermissionsAPITest(APITestCase):
    """Workspace membership gates task access through queryset + object permission."""

    def setUp(self):
        self.user = User.objects.create_user(username='tp@example.com', email='tp@example.com', password='x')
        self.org = Organization.objects.create(name='TP Org')
        self.ws = Workspace.objects.create(name='TP WS', organization=self.org)
        TeamMember.objects.create(workspace=self.ws, user=self.user)
        self.project = Project.objects.create(workspace=self.ws, name='TP')
        self.task = Task.objects.create(project=self.project, title='T')

    def test_member_has_object_permission_for_mutations(self):
        self.client.delete(f'/api/v1/tasks/{self.task.pk}/', **_jwt_header(self.user))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
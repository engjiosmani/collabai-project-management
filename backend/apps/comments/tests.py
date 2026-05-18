from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from apps.workspaces.models import TeamMember
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority
from .models import Comment, ActivityLog

User = get_user_model()

def _jwt_header(user):
    refresh = RefreshToken.for_user(user)
    return {
        "HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"
    }

class CommentModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="commentuser", password="test12345")
        self.org = Organization.objects.create(name="Comment Org")
        self.workspace = Workspace.objects.create(name="Comment Workspace", organization=self.org)
        self.project = Project.objects.create(workspace=self.workspace, name="Comment Project")
        self.status = TaskStatus.objects.create(name="In Progress Test")
        self.priority = TaskPriority.objects.create(name="Medium", level=2)
        self.task = Task.objects.create(
            project=self.project,
            title="Comment Task",
            status=self.status,
            priority=self.priority
        )

    def test_create_comment(self):
        comment = Comment.objects.create(
            task=self.task,
            author=self.user,
            content="This is a comment"
        )

        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.author, self.user)

    def test_create_activity_log(self):
        activity = ActivityLog.objects.create(
            task=self.task,
            user=self.user,
            action="TASK_CREATED",
            description="Task was created"
        )

        self.assertEqual(activity.task, self.task)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.action, "TASK_CREATED")

class CommentCRUDAPITest(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='auth@example.com', email='auth@example.com', password='x')
        self.other_member = User.objects.create_user(username='oth@example.com', email='oth@example.com', password='x')
        self.outsider = User.objects.create_user(username='cout@example.com', email='cout@example.com', password='x')
        self.org = Organization.objects.create(name='Com Org')
        self.workspace = Workspace.objects.create(name='Com WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.author)
        TeamMember.objects.create(workspace=self.workspace, user=self.other_member)
        self.project = Project.objects.create(workspace=self.workspace, name='Com Proj')
        self.status = TaskStatus.objects.create(name='S')
        self.priority = TaskPriority.objects.create(name='P', level=1)
        self.task = Task.objects.create(project=self.project, title='Com Task', status=self.status, priority=self.priority)
        self.comment = Comment.objects.create(task=self.task, author=self.author, content='Hello')

    def test_create_sets_author_from_jwt_user(self):
        res = self.client.post(
            '/api/v1/comments/',
            {'task': self.task.pk, 'content': 'New note'},
            format='json',
            **_jwt_header(self.author),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['author'], self.author.pk)

    def test_non_author_member_cannot_patch_or_delete(self):
        res = self.client.patch(
            f'/api/v1/comments/{self.comment.pk}/',
            {'content': 'hacked'},
            format='json',
            **_jwt_header(self.other_member),
        )
        self.assertEqual(res.status_code, 403)

        res = self.client.delete(f'/api/v1/comments/{self.comment.pk}/', **_jwt_header(self.other_member))
        self.assertEqual(res.status_code, 403)

    def test_author_can_update_delete(self):
        res = self.client.patch(
            f'/api/v1/comments/{self.comment.pk}/',
            {'content': 'edited'},
            format='json',
            **_jwt_header(self.author),
        )
        self.assertEqual(res.status_code, 200)

        res = self.client.delete(f'/api/v1/comments/{self.comment.pk}/', **_jwt_header(self.author))
        self.assertEqual(res.status_code, 204)

    def test_blank_content_rejected(self):
        res = self.client.post(
            '/api/v1/comments/',
            {'task': self.task.pk, 'content': '   '},
            format='json',
            **_jwt_header(self.author),
        )
        self.assertEqual(res.status_code, 400)

    def test_list_supports_filter_search_ordering(self):
        alpha = Comment.objects.create(task=self.task, author=self.author, content='Alpha comment search')
        zulu = Comment.objects.create(task=self.task, author=self.author, content='Zulu comment search')

        now = timezone.now()
        Comment.objects.filter(pk=alpha.pk).update(created_at=now - timedelta(minutes=1))
        Comment.objects.filter(pk=zulu.pk).update(created_at=now)

        res = self.client.get(
            f'/api/v1/comments/?task={self.task.pk}&search=search&ordering=created_at&page_size=1',
            **_jwt_header(self.author),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['content'], 'Alpha comment search')


class ActivityLogReadOnlyAPITest(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='alog@example.com', email='alog@example.com', password='x')
        self.org = Organization.objects.create(name='AL Org')
        self.workspace = Workspace.objects.create(name='AL WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.member)
        self.project = Project.objects.create(workspace=self.workspace, name='AL Proj')
        self.status = TaskStatus.objects.create(name='S2')
        self.priority = TaskPriority.objects.create(name='P2', level=2)
        self.task = Task.objects.create(project=self.project, title='AL Task', status=self.status, priority=self.priority)
        self.log = ActivityLog.objects.create(
            task=self.task,
            user=self.member,
            action='UPDATED',
            description='x',
        )

    def test_list_and_retrieve_read_only(self):
        res = self.client.get('/api/v1/activity-logs/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['results'][0]['task_title'], self.task.title)
        self.assertEqual(res.data['results'][0]['user_email'], self.member.email)

        res = self.client.get(f'/api/v1/activity-logs/{self.log.pk}/', **_jwt_header(self.member))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['task_title'], self.task.title)
        self.assertEqual(res.data['user_email'], self.member.email)

    def test_post_not_allowed(self):
        res = self.client.post(
            '/api/v1/activity-logs/',
            {'task': self.task.pk, 'action': 'X'},
            format='json',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 405)

    def test_activity_log_filter_and_ordering(self):
        ActivityLog.objects.create(task=self.task, user=self.member, action='ALPHA', description='a')
        ActivityLog.objects.create(task=self.task, user=self.member, action='ZULU', description='z')

        res = self.client.get(
            f'/api/v1/activity-logs/?task={self.task.pk}&ordering=action&page_size=1',
            **_jwt_header(self.member),
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['action'], 'ALPHA')


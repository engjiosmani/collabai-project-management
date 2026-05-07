from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority
from .models import Comment, ActivityLog

User = get_user_model()


class CommentModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="commentuser", password="test12345")
        self.org = Organization.objects.create(name="Comment Org")
        self.workspace = Workspace.objects.create(name="Comment Workspace", organization=self.org)
        self.project = Project.objects.create(workspace=self.workspace, name="Comment Project")
        self.status = TaskStatus.objects.create(name="In Progress")
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
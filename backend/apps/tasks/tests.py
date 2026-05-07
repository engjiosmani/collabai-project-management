from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from apps.projects.models import Project
from .models import Task, TaskStatus, TaskPriority, Label, TaskLabel, Attachment

User = get_user_model()


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
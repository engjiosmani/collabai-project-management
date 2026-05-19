from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority
from .models import AIRequest, CacheEntity

User = get_user_model()


class AIModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aiuser", password="test12345")
        self.org = Organization.objects.create(name="AI Org")
        self.project = Project.objects.create(organization=self.org, name="AI Project")
        self.status = TaskStatus.objects.create(name="Review")
        self.priority = TaskPriority.objects.create(name="Low", level=3)
        self.task = Task.objects.create(
            project=self.project,
            title="AI Task",
            status=self.status,
            priority=self.priority
        )

    def test_create_ai_request(self):
        ai_request = AIRequest.objects.create(
            user=self.user,
            task=self.task,
            prompt="Summarize this task",
            response="Task summary",
            status="completed"
        )

        self.assertEqual(ai_request.user, self.user)
        self.assertEqual(ai_request.task, self.task)
        self.assertEqual(ai_request.status, "completed")

    def test_create_cache_entity(self):
        cache = CacheEntity.objects.create(
            key="task-summary-1",
            value={"summary": "Cached summary"}
        )

        self.assertEqual(cache.key, "task-summary-1")
        self.assertEqual(cache.value["summary"], "Cached summary")
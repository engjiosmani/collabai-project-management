from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from .models import Project, ProjectMember, Subscription, Integration

User = get_user_model()


class ProjectModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="projectuser", password="test12345")
        self.org = Organization.objects.create(name="Test Organization")
        self.workspace = Workspace.objects.create(name="Test Workspace", organization=self.org)

    def test_create_project(self):
        project = Project.objects.create(
            workspace=self.workspace,
            name="CollabAI Project",
            description="Project management system"
        )

        self.assertEqual(project.workspace, self.workspace)
        self.assertEqual(project.name, "CollabAI Project")

    def test_create_project_member(self):
        project = Project.objects.create(workspace=self.workspace, name="Project A")
        member = ProjectMember.objects.create(project=project, user=self.user)

        self.assertEqual(member.project, project)
        self.assertEqual(member.user, self.user)

    def test_create_subscription(self):
        subscription = Subscription.objects.create(
            workspace=self.workspace,
            plan_name="Free"
        )

        self.assertEqual(subscription.workspace, self.workspace)
        self.assertTrue(subscription.is_active)

    def test_create_integration(self):
        integration = Integration.objects.create(
            workspace=self.workspace,
            name="GitHub",
            provider="github"
        )

        self.assertEqual(integration.workspace, self.workspace)
        self.assertEqual(integration.provider, "github")
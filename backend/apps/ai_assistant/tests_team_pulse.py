from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import TeamMember, Workspace

from .models import GitHubWorkspaceConfig, TeamPulseAlert
from .services.team_pulse.workload import build_workload_alerts, compute_member_workloads

User = get_user_model()


def _jwt(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    RAG_AUTO_INDEX=False,
    RAG_FORCE_MEMORY_STORE=True,
)
class WorkloadAnalyzerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pulse@example.com',
            email='pulse@example.com',
            password='x',
        )
        self.org = Organization.objects.create(name='Pulse Org')
        self.workspace = Workspace.objects.create(name='Pulse WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.user)
        self.project = Project.objects.create(workspace=self.workspace, name='Pulse Proj')
        self.status = TaskStatus.objects.create(name='To Do')
        self.priority = TaskPriority.objects.create(name='High', level=4)

    def test_workload_and_burnout_alert(self):
        for i in range(11):
            Task.objects.create(
                project=self.project,
                title=f'Task {i}',
                status=self.status,
                priority=self.priority,
                assigned_to=self.user,
            )

        workloads = compute_member_workloads(self.workspace.pk)
        self.assertEqual(len(workloads), 1)
        self.assertGreaterEqual(workloads[0].active_tasks, 10)

        alerts = build_workload_alerts(self.workspace.pk, workloads)
        self.assertTrue(any(a['alert_type'] == 'burnout_risk' for a in alerts))


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    RAG_AUTO_INDEX=False,
    RAG_FORCE_MEMORY_STORE=True,
)
class TeamPulseAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='api@example.com',
            email='api@example.com',
            password='x',
        )
        self.org = Organization.objects.create(name='API Org')
        self.workspace = Workspace.objects.create(name='API WS', organization=self.org)
        TeamMember.objects.create(workspace=self.workspace, user=self.user)

    def test_github_config_and_run(self):
        res = self.client.put(
            '/api/v1/ai/team-pulse/github/',
            {
                'workspace_id': self.workspace.pk,
                'repos': ['acme/demo'],
                'member_github_logins': {str(self.user.pk): 'octocat'},
                'is_enabled': True,
            },
            format='json',
            **_jwt(self.user),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(GitHubWorkspaceConfig.objects.filter(workspace=self.workspace).exists())

        res = self.client.post(
            '/api/v1/ai/team-pulse/run/',
            {'workspace_id': self.workspace.pk, 'run_type': 'workload'},
            format='json',
            **_jwt(self.user),
        )
        self.assertIn(res.status_code, (200, 202), res.data)

        res = self.client.get(
            f'/api/v1/ai/team-pulse/?workspace_id={self.workspace.pk}',
            **_jwt(self.user),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('alerts', res.data)

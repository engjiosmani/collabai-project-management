from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus

from .models import GitHubOrganizationConfig
from .services.team_pulse.standup import _member_to_markdown, _standup_field_text

User = get_user_model()


def _jwt(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


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
        OrganizationMember.objects.create(organization=self.org, user=self.user)
        self.project = Project.objects.create(organization=self.org, name='API Proj')
        self.status, _ = TaskStatus.objects.get_or_create(name='To Do')

    def test_github_config_and_run(self):
        res = self.client.put(
            '/api/v1/ai/team-pulse/github/',
            {
                'organization_id': self.org.pk,
                'repos': ['acme/demo'],
                'member_github_logins': {str(self.user.pk): 'octocat'},
                'is_enabled': True,
            },
            format='json',
            **_jwt(self.user),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(GitHubOrganizationConfig.objects.filter(organization=self.org).exists())

        Task.objects.create(
            project=self.project,
            title='Recent task',
            status=self.status,
            assigned_to=self.user,
        )

        res = self.client.post(
            '/api/v1/ai/team-pulse/run/',
            {'organization_id': self.org.pk, 'run_type': 'standup'},
            format='json',
            **_jwt(self.user),
        )
        self.assertIn(res.status_code, (200, 202), res.data)
        if res.status_code == 200:
            payload = res.data.get('standup', {}).get('payload', {})
            members = payload.get('members', [])
            if members and members[0].get('tasks_changed'):
                task_row = members[0]['tasks_changed'][0]
                self.assertIsInstance(task_row.get('updated_at'), str)

        res = self.client.get(
            f'/api/v1/ai/team-pulse/?organization_id={self.org.pk}',
            **_jwt(self.user),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('latest_standup', res.data)
        self.assertNotIn('standup_delivery', res.data)


class StandupFormattingTest(TestCase):
    def test_dict_ai_output_becomes_bullets(self):
        text = _standup_field_text(
            {
                'tasks': ['Implement dashboard', 'Fix login'],
                'commits': ['Merge PR #39'],
            }
        )
        self.assertIn('Tasks', text)
        self.assertIn('- Implement dashboard', text)
        self.assertNotIn("{'tasks'", text)

    def test_member_markdown_has_headings(self):
        md = _member_to_markdown(
            {
                'email': 'user@example.com',
                'yesterday': 'No recorded activity.',
                'today': 'Focus on **3 open task(s)**.',
                'blockers': 'None identified.',
            }
        )
        self.assertIn('## user@example.com', md)
        self.assertIn('### Yesterday', md)
        self.assertIn('### Today', md)

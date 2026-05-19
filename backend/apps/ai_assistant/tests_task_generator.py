from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project

from .models import PlannedTask, ProjectPlanDraft
from .services.task_generator import PlanMaterializer, TaskGeneratorService
from .services.task_generator.json_utils import normalize_plan

SAMPLE_PLAN = {
    'project_name': 'Test App',
    'project_description': 'A distributed systems demo project.',
    'sprint_count': 1,
    'sprints': [
        {
            'sprint_number': 1,
            'sprint_name': 'Sprint 1',
            'goal': 'Build foundations',
            'tasks': [
                {
                    'slug': 'DB-01',
                    'title': 'DB-01: Core models',
                    'category': 'db',
                    'labels': ['backend', 'db', 'priority:high'],
                    'story_points': 5,
                    'suggested_assignee_user_id': None,
                    'suggested_assignee_role': 'Backend Developer',
                    'depends_on': [],
                    'scope_tags': ['database', 'models'],
                    'goal': 'Create core ORM models.',
                    'description': 'Define models and migrations.',
                    'subtasks': ['Create User model', 'Run migrate'],
                    'acceptance_criteria': ['Migrations apply cleanly'],
                }
            ],
        }
    ],
    'validation': {
        'is_complete': True,
        'covered_themes': ['database', 'models'],
        'warnings': [],
    },
}

SAMPLE_VALIDATION = {
    'is_complete': True,
    'covered_themes': ['database', 'models'],
    'missing_themes': [],
    'additional_tasks': [],
    'warnings': [],
}


@override_settings(
    RAG_FORCE_MEMORY_STORE=True,
    GROQ_API_KEY='test-key',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class NormalizePlanTests(TestCase):
    def test_fills_missing_slug(self):
        plan = {
            'sprints': [
                {
                    'sprint_number': 1,
                    'tasks': [{'title': 'Set up API', 'category': 'api'}],
                }
            ]
        }
        normalize_plan(plan)
        slug = plan['sprints'][0]['tasks'][0]['slug']
        self.assertTrue(slug)
        self.assertIn(slug, plan['sprints'][0]['tasks'][0]['title'])


class TaskGeneratorServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='planner@example.com',
            email='planner@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='Plan Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )

    @patch.object(TaskGeneratorService, '_call_json')
    def test_generate_persists_planned_tasks(self, mock_json):
        mock_json.side_effect = [SAMPLE_PLAN, SAMPLE_VALIDATION]
        draft = ProjectPlanDraft.objects.create(
            user=self.user,
            organization=self.org,
            input_description='Build a task app',
            sprint_count=1,
            team_members=[{'user_id': self.user.pk, 'username': 'planner', 'role': 'Backend Developer'}],
        )
        TaskGeneratorService().run_generation(draft.pk)
        draft.refresh_from_db()
        self.assertEqual(draft.status, ProjectPlanDraft.Status.PENDING_APPROVAL)
        self.assertEqual(draft.planned_tasks.count(), 1)
        self.assertIn('## Goal', draft.planned_tasks.first().rendered_body)

    def test_approve_creates_project_and_tasks(self):
        draft = ProjectPlanDraft.objects.create(
            user=self.user,
            organization=self.org,
            input_description='Build a task app',
            sprint_count=1,
            status=ProjectPlanDraft.Status.PENDING_APPROVAL,
            ai_raw_output=SAMPLE_PLAN,
        )
        TaskGeneratorService().persist_plan(draft, SAMPLE_PLAN)
        project = PlanMaterializer().approve(draft)
        self.assertIsInstance(project, Project)
        self.assertEqual(project.tasks.count(), 1)
        draft.refresh_from_db()
        self.assertEqual(draft.status, ProjectPlanDraft.Status.SYNCED)

    def test_approve_creates_unique_name_when_project_exists(self):
        Project.objects.create(organization=self.org, name='Task App')
        draft = ProjectPlanDraft.objects.create(
            user=self.user,
            organization=self.org,
            input_description='Build a task app',
            sprint_count=1,
            status=ProjectPlanDraft.Status.PENDING_APPROVAL,
            ai_raw_output={**SAMPLE_PLAN, 'project_name': 'Task App'},
        )
        TaskGeneratorService().persist_plan(draft, draft.ai_raw_output)
        project = PlanMaterializer().approve(draft)
        self.assertEqual(project.name, 'Task App (2)')

    def test_approve_adds_tasks_to_existing_project(self):
        existing = Project.objects.create(organization=self.org, name='Existing App')
        draft = ProjectPlanDraft.objects.create(
            user=self.user,
            organization=self.org,
            input_description='Add features',
            sprint_count=1,
            status=ProjectPlanDraft.Status.PENDING_APPROVAL,
            ai_raw_output=SAMPLE_PLAN,
            target_project=existing,
        )
        TaskGeneratorService().persist_plan(draft, SAMPLE_PLAN)
        before_count = existing.tasks.count()
        project = PlanMaterializer().approve(draft)
        self.assertEqual(project.pk, existing.pk)
        self.assertEqual(existing.tasks.count(), before_count + 1)
        self.assertFalse(getattr(project, '_created_new_for_plan', True))


@override_settings(
    RAG_FORCE_MEMORY_STORE=True,
    GROQ_API_KEY='test-key',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class TaskGeneratorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='api-planner@example.com',
            email='api-planner@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='API Plan Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    @patch('apps.ai_assistant.views_task_generator.generate_task_plan.delay')
    def test_create_plan_with_target_project(self, mock_delay):
        mock_delay.return_value = MagicMock(id='celery-id')
        existing = Project.objects.create(organization=self.org, name='Target Project')
        response = self.client.post(
            reverse('ai-task-plan-create'),
            {
                'organization_id': self.org.pk,
                'description': 'Add auth tasks to existing app.',
                'sprint_count': 1,
                'target_project_id': existing.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        draft = ProjectPlanDraft.objects.get(pk=response.data['plan_id'])
        self.assertEqual(draft.target_project_id, existing.pk)

    @patch('apps.ai_assistant.views_task_generator.generate_task_plan.delay')
    def test_create_plan_returns_202(self, mock_delay):
        mock_delay.return_value = MagicMock(id='celery-id')
        response = self.client.post(
            reverse('ai-task-plan-create'),
            {
                'organization_id': self.org.pk,
                'description': 'Distributed systems ecommerce app with JWT and Redis.',
                'sprint_count': 2,
                'team_members': [
                    {
                        'user_id': self.user.pk,
                        'username': self.user.username,
                        'role': 'Backend Developer',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('plan_id', response.data)
        draft = ProjectPlanDraft.objects.get(pk=response.data['plan_id'])
        self.assertEqual(draft.status, ProjectPlanDraft.Status.GENERATING)

    def test_get_plan_detail(self):
        draft = ProjectPlanDraft.objects.create(
            user=self.user,
            organization=self.org,
            input_description='Test',
            status=ProjectPlanDraft.Status.PENDING_APPROVAL,
            ai_raw_output=SAMPLE_PLAN,
        )
        PlannedTask.objects.create(
            plan=draft,
            slug='DB-01',
            title='DB-01: Core models',
            sprint_number=1,
            story_points=5,
            order=1,
        )
        response = self.client.get(reverse('ai-task-plan-detail', kwargs={'plan_id': draft.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['task_count'], 1)

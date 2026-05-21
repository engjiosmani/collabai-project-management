from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.workspaces.models import JobRole, TeamMember, Workspace
from apps.workspaces.services.job_role_assignment import apply_job_role_assignments


class JobRoleAssignmentTests(TestCase):
    def setUp(self):
        self.backend, _ = JobRole.objects.get_or_create(
            code='backend_developer',
            defaults={'name': 'Backend Developer', 'task_categories': ['backend', 'api']},
        )
        self.frontend, _ = JobRole.objects.get_or_create(
            code='frontend_developer',
            defaults={'name': 'Frontend Developer', 'task_categories': ['frontend']},
        )
        self.user_backend = get_user_model().objects.create_user(
            username='be@example.com', email='be@example.com', password='pass',
        )
        self.user_frontend = get_user_model().objects.create_user(
            username='fe@example.com', email='fe@example.com', password='pass',
        )

    def test_assigns_by_category(self):
        plan = {
            'sprints': [{
                'sprint_number': 1,
                'tasks': [
                    {
                        'slug': 'API-01',
                        'category': 'api',
                        'suggested_assignee_user_id': None,
                        'suggested_assignee_role': '',
                    },
                    {
                        'slug': 'FE-01',
                        'category': 'frontend',
                        'suggested_assignee_user_id': 999,
                        'suggested_assignee_role': '',
                    },
                ],
            }]
        }
        team = [
            {'user_id': self.user_backend.pk, 'role': 'Backend Developer', 'task_categories': ['backend', 'api']},
            {'user_id': self.user_frontend.pk, 'role': 'Frontend Developer', 'task_categories': ['frontend']},
        ]
        result = apply_job_role_assignments(plan, team)
        tasks = result['sprints'][0]['tasks']
        self.assertEqual(tasks[0]['suggested_assignee_user_id'], self.user_backend.pk)
        self.assertEqual(tasks[1]['suggested_assignee_user_id'], self.user_frontend.pk)


class JobRoleSeedTests(TestCase):
    def test_seed_migration_roles_exist(self):
        self.assertTrue(JobRole.objects.filter(code='devops_engineer').exists())
        self.assertTrue(JobRole.objects.filter(code='backend_developer').exists())
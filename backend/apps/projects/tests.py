from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.workspaces.models import TeamMember

from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from .models import Project, ProjectMember, Subscription, Integration

User = get_user_model()

def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


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

        class ProjectCRUDAPITest(APITestCase):
            def setUp(self):
                self.member = User.objects.create_user(username='mem@example.com', email='mem@example.com',
                                                       password='x')
                self.outsider = User.objects.create_user(username='out@example.com', email='out@example.com',
                                                         password='x')
                self.org = Organization.objects.create(name='API Org')
                self.workspace = Workspace.objects.create(name='API WS', organization=self.org)
                TeamMember.objects.create(workspace=self.workspace, user=self.member)
                self.project = Project.objects.create(workspace=self.workspace, name='Seed Project')

            def test_list_requires_authentication(self):
                res = self.client.get('/api/v1/projects/')
                self.assertEqual(res.status_code, 401)

            def test_member_can_list_and_retrieve(self):
                res = self.client.get('/api/v1/projects/', **_jwt_header(self.member))
                self.assertEqual(res.status_code, 200)
                self.assertGreaterEqual(len(res.data.get('results', res.data)), 1)

                res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(self.member))
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.data['name'], 'Seed Project')

            def test_outsider_cannot_see_foreign_project(self):
                res = self.client.get(f'/api/v1/projects/{self.project.pk}/', **_jwt_header(self.outsider))
                self.assertEqual(res.status_code, 404)

            def test_member_can_create_update_delete(self):
                create = self.client.post(
                    '/api/v1/projects/',
                    {
                        'workspace': self.workspace.pk,
                        'name': 'New API Project',
                        'description': 'd',
                        'is_active': True,
                    },
                    format='json',
                    **_jwt_header(self.member),
                )
                self.assertEqual(create.status_code, 201, create.data)
                pid = create.data['id']

                patch = self.client.patch(
                    f'/api/v1/projects/{pid}/',
                    {'description': 'updated'},
                    format='json',
                    **_jwt_header(self.member),
                )
                self.assertEqual(patch.status_code, 200)
                self.assertEqual(patch.data['description'], 'updated')

                delete = self.client.delete(f'/api/v1/projects/{pid}/', **_jwt_header(self.member))
                self.assertEqual(delete.status_code, 204)

            def test_duplicate_name_per_workspace_returns_400(self):
                res = self.client.post(
                    '/api/v1/projects/',
                    {'workspace': self.workspace.pk, 'name': 'Seed Project'},
                    format='json',
                    **_jwt_header(self.member),
                )
                self.assertEqual(res.status_code, 400)

            def test_outsider_cannot_create_in_workspace(self):
                res = self.client.post(
                    '/api/v1/projects/',
                    {'workspace': self.workspace.pk, 'name': 'Hack'},
                    format='json',
                    **_jwt_header(self.outsider),
                )
                self.assertEqual(res.status_code, 400)

        class ProjectLoginJWTAuthTest(APITestCase):
            """Ensures real JWT from login works with project endpoints."""

            def setUp(self):
                self.user = User.objects.create_user(username='jwt@example.com', email='jwt@example.com',
                                                     password='SecretPass123!')
                self.org = Organization.objects.create(name='JWT Org')
                self.ws = Workspace.objects.create(name='JWT WS', organization=self.org)
                TeamMember.objects.create(workspace=self.ws, user=self.user)

            def test_login_then_access_projects(self):
                login = self.client.post(
                    '/api/v1/auth/login',
                    {'email': 'jwt@example.com', 'password': 'SecretPass123!'},
                    format='json',
                )
                self.assertEqual(login.status_code, 200, login.data)
                token = login.data['access']
                res = self.client.get('/api/v1/projects/', HTTP_AUTHORIZATION=f'Bearer {token}')
                self.assertEqual(res.status_code, 200)
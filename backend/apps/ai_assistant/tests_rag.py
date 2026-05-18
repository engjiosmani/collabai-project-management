from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comments.models import Comment
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import Role, TeamMember, Workspace

from .services.indexing import document_from_task, index_instance
from .services.rag import RAGService
from .services.vector_store import MemoryVectorStore, reset_vector_store


@override_settings(
    RAG_FORCE_MEMORY_STORE=True,
    RAG_AUTO_INDEX=False,
    GROQ_API_KEY='test-key',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class RAGServiceTests(TestCase):
    def setUp(self):
        reset_vector_store()
        self.user = get_user_model().objects.create_user(
            username='raguser@example.com',
            email='raguser@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='RAG Org')
        self.workspace = Workspace.objects.create(name='RAG WS', organization=self.org)
        member_role = Role.objects.create(workspace=self.workspace, name=Role.MEMBER)
        TeamMember.objects.create(workspace=self.workspace, user=self.user, role=member_role)
        self.project = Project.objects.create(
            workspace=self.workspace,
            name='Auth Project',
            description='JWT authentication rollout',
        )
        self.status = TaskStatus.objects.create(name='Open')
        self.priority = TaskPriority.objects.create(name='High', level=1)
        self.task = Task.objects.create(
            project=self.project,
            title='AUTH-02 Login JWT',
            description='Implement JWT login with refresh tokens',
            status=self.status,
            priority=self.priority,
        )
        Comment.objects.create(
            task=self.task,
            author=self.user,
            content='Po përdorim refresh tokens 60min/7 ditë',
        )

    def test_document_from_task_shape(self):
        doc = document_from_task(self.task)
        self.assertEqual(doc['doc_type'], 'task')
        self.assertIn('JWT', doc['content'])

    @patch('apps.ai_assistant.services.embeddings.EmbeddingService.embed_text')
    def test_semantic_search_finds_auth_related_task(self, mock_embed):
        mock_embed.side_effect = lambda text: (
            [1.0, 0.0, 0.0] if 'autentikim' in text.lower() else [0.9, 0.1, 0.0]
        )
        index_instance(self.task, embedding_service=MagicMock(embed_text=mock_embed))

        hits = RAGService(embedding_service=MagicMock(embed_text=mock_embed)).semantic_search(
            workspace_id=self.workspace.pk,
            query='autentikim',
            top_k=3,
        )
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0]['doc_type'], 'task')

    @patch('apps.ai_assistant.services.rag.GroqClient.chat')
    @patch('apps.ai_assistant.services.embeddings.EmbeddingService.embed_text')
    def test_rag_ask_returns_answer(self, mock_embed, mock_chat):
        mock_embed.return_value = [1.0, 0.0, 0.0]
        mock_chat.return_value = 'Po, përdorim JWT.\n\nBurime: [task #1]'
        index_instance(self.task, embedding_service=MagicMock(embed_text=mock_embed))

        result = RAGService(embedding_service=MagicMock(embed_text=mock_embed)).ask(
            user=self.user,
            workspace_id=self.workspace.pk,
            question='A kemi JWT?',
        )
        self.assertIn('JWT', result['answer'])
        self.assertTrue(result['sources'])


@override_settings(
    RAG_FORCE_MEMORY_STORE=True,
    RAG_AUTO_INDEX=False,
    GROQ_API_KEY='test-key',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class RAGAPITests(TestCase):
    def setUp(self):
        reset_vector_store()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='api@example.com',
            email='api@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='API Org')
        self.workspace = Workspace.objects.create(name='API WS', organization=self.org)
        member_role = Role.objects.create(workspace=self.workspace, name=Role.MEMBER)
        TeamMember.objects.create(workspace=self.workspace, user=self.user, role=member_role)
        self.project = Project.objects.create(workspace=self.workspace, name='P1')
        self.status = TaskStatus.objects.create(name='Todo')
        self.priority = TaskPriority.objects.create(name='Med', level=2)
        self.task = Task.objects.create(
            project=self.project,
            title='JWT auth endpoint',
            description='login refresh logout',
            status=self.status,
            priority=self.priority,
        )
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    @patch('apps.ai_assistant.services.embeddings.EmbeddingService.embed_text')
    def test_semantic_search_endpoint(self, mock_embed):
        mock_embed.return_value = [1.0, 0.0, 0.0]
        index_instance(self.task, embedding_service=MagicMock(embed_text=mock_embed))

        url = reverse('ai-semantic-search')
        response = self.client.post(
            url,
            {
                'workspace_id': self.workspace.pk,
                'query': 'autentikim',
                'top_k': 5,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    @patch('apps.ai_assistant.views.RAGService.ask')
    def test_rag_query_endpoint(self, mock_ask):
        mock_ask.return_value = {
            'answer': 'JWT u zgjodh për multi-device.',
            'sources': [{'doc_type': 'task', 'doc_id': '1', 'score': 0.9}],
            'request_id': 1,
        }
        response = self.client.post(
            reverse('ai-rag-query'),
            {
                'workspace_id': self.workspace.pk,
                'question': 'Pse JWT?',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('answer', response.data)

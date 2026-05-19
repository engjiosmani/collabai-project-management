from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ai_assistant.models import AIRequest
from apps.ai_assistant.services.text_analysis import TextAnalysisService
from apps.organizations.models import Organization, OrganizationMember


@override_settings(GROQ_API_KEY='test-key')
class TextAnalysisServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='analyze@example.com',
            email='analyze@example.com',
            password='StrongPass123!',
        )

    @patch('apps.ai_assistant.services.text_analysis.GroqClient.chat')
    def test_analyze_summary_persists_request(self, mock_chat):
        mock_chat.return_value = '- Point one\n- Point two'
        result = TextAnalysisService().analyze(
            user=self.user,
            text='Long meeting notes about sprint planning.',
            mode='summary',
        )
        self.assertEqual(result['mode'], 'summary')
        self.assertIn('Point one', result['result'])
        record = AIRequest.objects.get(pk=result['request_id'])
        self.assertEqual(record.status, 'completed')


@override_settings(GROQ_API_KEY='test-key')
class TextAnalyzeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='api-analyze@example.com',
            email='api-analyze@example.com',
            password='StrongPass123!',
        )
        self.org = Organization.objects.create(name='Analyze Org')
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMember.MEMBER,
        )
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    @patch('apps.ai_assistant.views.TextAnalysisService.analyze')
    def test_analyze_endpoint(self, mock_analyze):
        mock_analyze.return_value = {
            'mode': 'action_items',
            'result': '- [ ] Ship API docs',
            'request_id': 99,
        }
        response = self.client.post(
            reverse('ai-text-analyze'),
            {'text': 'We need to ship API docs this week.', 'mode': 'action_items'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mode'], 'action_items')
        mock_analyze.assert_called_once()

    def test_analyze_requires_auth(self):
        client = APIClient()
        response = client.post(
            reverse('ai-text-analyze'),
            {'text': 'hello', 'mode': 'summary'},
            format='json',
        )
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_analyze_rejects_invalid_mode(self):
        response = self.client.post(
            reverse('ai-text-analyze'),
            {'text': 'hello', 'mode': 'invalid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

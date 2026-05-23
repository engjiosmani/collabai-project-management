from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ai_assistant.services.chatbot import ChatBotService


@override_settings(GROQ_API_KEY='test-key')
class ChatBotServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='chatbot@example.com',
            email='chatbot@example.com',
            password='pass12345',
        )

    @patch('apps.ai_assistant.services.chatbot.GroqClient.chat_messages')
    def test_reply_returns_answer(self, mock_chat):
        mock_chat.return_value = 'Hello! How can I help?'
        result = ChatBotService().reply(user=self.user, message='Hi', history=[])
        self.assertEqual(result['answer'], 'Hello! How can I help?')
        mock_chat.assert_called_once()


@override_settings(GROQ_API_KEY='test-key')
class ChatBotAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='api-chatbot@example.com',
            email='api-chatbot@example.com',
            password='pass12345',
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    @patch('apps.ai_assistant.views.chatbot.ChatBotService.reply')
    def test_chatbot_endpoint(self, mock_reply):
        mock_reply.return_value = {'answer': 'Sure!', 'request_id': 1}
        response = self.client.post(
            reverse('ai-chatbot'),
            {'message': 'Help me plan my day'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['answer'], 'Sure!')

    def test_chatbot_requires_auth(self):
        client = APIClient()
        response = client.post(reverse('ai-chatbot'), {'message': 'Hi'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

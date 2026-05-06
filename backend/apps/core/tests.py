from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')

    def test_user_can_register_with_valid_credentials(self):
        response = self.client.post(
            self.url,
            {
                'email': 'test@example.com',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertNotIn('password', response.data)

        user = get_user_model().objects.get(email='test@example.com')
        self.assertNotEqual(user.password, 'StrongPass123!')
        self.assertTrue(user.check_password('StrongPass123!'))

    def test_duplicate_email_is_rejected(self):
        get_user_model().objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='StrongPass123!',
        )

        response = self.client.post(
            self.url,
            {
                'email': 'test@example.com',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                'email': 'weak@example.com',
                'password': 'password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('login')
        self.refresh_url = reverse('token_refresh')
        self.logout_url = reverse('logout')
        self.user = get_user_model().objects.create_user(
            username='auth@example.com',
            email='auth@example.com',
            password='StrongPass123!',
        )

    def test_valid_credentials_return_tokens(self):
        response = self.client.post(
            self.login_url,
            {'email': 'auth@example.com', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_wrong_password_returns_400(self):
        response = self.client.post(
            self.login_url,
            {'email': 'auth@example.com', 'password': 'WrongPass!1'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_returns_400(self):
        response = self.client.post(
            self.login_url,
            {'email': 'no@example.com', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_returns_new_access_token(self):
        refresh = str(RefreshToken.for_user(self.user))
        response = self.client.post(
            self.refresh_url,
            {'refresh': refresh},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_with_invalid_token_returns_400(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': 'not.a.valid.token'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_valid_token_blacklists_refresh_and_prevents_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)

        # Authenticate using access token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # Logout -> blacklist refresh token
        response = self.client.post(
            self.logout_url,
            {'refresh': refresh_str},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Now refresh should fail because token is blacklisted
        response2 = self.client.post(
            self.refresh_url,
            {'refresh': refresh_str},
            format='json',
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_refresh_token_in_body(self):
            refresh = RefreshToken.for_user(self.user)
            access = str(refresh.access_token)

            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
            response = self.client.post(self.logout_url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('refresh', response.data)
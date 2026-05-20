from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from common.permissions import HasAnyRole
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


class MiddlewareTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.logout_url = reverse('logout')
        self.user = get_user_model().objects.create_user(
            username='middleware@example.com',
            email='middleware@example.com',
            password='StrongPass123!',
        )

    def test_request_logging_adds_request_id_header_and_logs_metadata(self):
        with self.assertLogs('config.middleware', level='INFO') as logs:
            response = self.client.post(
                self.register_url,
                {'email': 'new@example.com', 'password': 'StrongPass123!'},
                HTTP_X_REQUEST_ID='req-test-123',
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['X-Request-ID'], 'req-test-123')
        log_line = '\n'.join(logs.output)
        self.assertIn('request_id=req-test-123', log_line)
        self.assertIn('method=POST', log_line)
        self.assertIn('endpoint=/api/v1/auth/register', log_line)
        self.assertIn('status=201', log_line)
        self.assertIn('user_id=-', log_line)

    def test_protected_endpoint_rejects_unauthenticated_requests(self):
        response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_request_logs_user_id(self):
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        with self.assertLogs('config.middleware', level='INFO') as logs:
            response = self.client.post(self.logout_url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(f'user_id={self.user.id}', '\n'.join(logs.output))

    def test_invalid_bearer_returns_401_before_view(self):
        response = self.client.post(
            self.logout_url,
            {},
            HTTP_AUTHORIZATION='Bearer not.a.valid.jwt.segment',
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_public_route_allows_invalid_bearer_without_reject(self):
        response = self.client.post(
            self.register_url,
            {'email': 'public@example.com', 'password': 'StrongPass123!'},
            HTTP_AUTHORIZATION='Bearer invalid.token.here',
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_options_preflight_bypasses_jwt_enforcement(self):
        response = self.client.options(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @override_settings(
        API_JWT_ROLE_REQUIREMENTS=(
            ('/api/v1/auth/logout', ('middleware_rbac_demo',)),
        )
    )
    def test_jwt_rbac_denies_without_required_assignment(self):
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.post(self.logout_url, {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        API_JWT_ROLE_REQUIREMENTS=(
            ('/api/v1/auth/logout', ('middleware_rbac_demo',)),
        )
    )
    def test_jwt_rbac_allows_when_user_has_matching_group(self):
        group = Group.objects.create(name='middleware_rbac_demo')
        self.user.groups.add(group)
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.post(self.logout_url, {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class RBACPermissionTests(TestCase):
    def test_has_any_role_accepts_user_group_membership(self):
        user = get_user_model().objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='StrongPass123!',
        )
        group = Group.objects.create(name='owner')
        user.groups.add(group)

        request = type('Request', (), {'user': user})()
        view = type('View', (), {'required_roles': ('owner', 'admin')})()

        self.assertTrue(HasAnyRole().has_permission(request, view))

    def test_has_any_role_rejects_missing_role(self):
        user = get_user_model().objects.create_user(
            username='member@example.com',
            email='member@example.com',
            password='StrongPass123!',
        )
        request = type('Request', (), {'user': user})()
        view = type('View', (), {'required_roles': ('admin',)})()

        self.assertFalse(HasAnyRole().has_permission(request, view))


class OperationsEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            username='adminops@example.com',
            email='adminops@example.com',
            password='StrongPass123!',
            is_staff=True,
        )
        self.normal_user = get_user_model().objects.create_user(
            username='memberops@example.com',
            email='memberops@example.com',
            password='StrongPass123!',
        )

    def test_health_is_public(self):
        response = self.client.get('/api/v1/health/')
        self.assertIn(response.status_code, (200, 503))
        self.assertIn('status', response.data)

    def test_metrics_requires_admin(self):
        response = self.client.get('/api/v1/metrics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token = str(RefreshToken.for_user(self.normal_user).access_token)
        response = self.client.get('/api/v1/metrics/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        response = self.client.get('/api/v1/metrics/', HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('workspaces', response.data)

    def test_swagger_and_schema_available(self):
        schema = self.client.get('/api/schema/')
        docs = self.client.get('/api/docs/')
        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)


class ExceptionHandlerTests(TestCase):
    def test_custom_exception_handler_passes_through_drf_errors(self):
        from common.exceptions import custom_exception_handler
        from rest_framework.exceptions import ValidationError

        # A ValidationError is a DRF exception and should be processed by the standard handler
        exc = ValidationError({"field": ["Invalid input."]})
        context = {}
        response = custom_exception_handler(exc, context)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["field"], ["Invalid input."])

    @override_settings(DEBUG=True)
    def test_custom_exception_handler_exposes_message_in_debug_mode(self):
        from common.exceptions import custom_exception_handler

        # In debug mode (DEBUG=True), unhandled exceptions are still wrapped
        # in a sanitized JSON 500 response, but the raw exception message is
        # exposed in the body to aid local troubleshooting.
        exc = ValueError("Some unexpected error")
        context = {}
        response = custom_exception_handler(exc, context)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data['detail'], 'Some unexpected error')
        self.assertIn('request_id', response.data)
        self.assertIn('X-Request-ID', response)

    @override_settings(DEBUG=False)
    def test_custom_exception_handler_sanitizes_unhandled_errors_in_production(self):
        from common.exceptions import custom_exception_handler

        # In production (DEBUG=False), unhandled exception should be sanitized
        # and return HTTP 500 with a clean detail message plus a request_id
        # for log correlation. The X-Request-ID header is always present.
        exc = ValueError("Some unexpected database or internal error")
        context = {}
        response = custom_exception_handler(exc, context)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data['detail'], 'A server error occurred.')
        self.assertIn('request_id', response.data)
        self.assertIn('X-Request-ID', response)


from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from ..serializers import (
    AccessTokenResponseSerializer,
    DashboardSummarySerializer,
    DetailResponseSerializer,
    ForgotPasswordSerializer,
    HealthResponseSerializer,
    LoginSerializer,
    LogoutRequestSerializer,
    MetricsResponseSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TokenRefreshRequestSerializer,
    TokenResponseSerializer,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.db.models import Count
from django.db import connection
from django.utils import timezone
from django.conf import settings

from datetime import timedelta
from django.contrib.auth import get_user_model

from common.cache import (
    CachedGETMixin,
    NAMESPACE_DASHBOARD,
    NAMESPACE_METRICS,
    cache_backend_label,
    get_cached_payload,
    get_metrics_cache_timeout,
    make_fixed_key,
    set_cached_payload,
)
from common.tenant_access import organization_ids_for_request, organizations_queryset_for_user
from common.role_permissions import project_visibility_q, task_visibility_q
from apps.comments.models import ActivityLog, Comment
from apps.comments.serializers import ActivityLogSerializer
from apps.notifications.models import Notification
from apps.organizations.models import Organization, OrganizationInvite
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.tasks.status_utils import completed_task_status_ids
from apps.workspaces.models import TeamMember, Workspace


@extend_schema(
    tags=['Authentication'],
    request=RegisterSerializer,
    responses={
        201: RegisterSerializer,
        400: OpenApiResponse(description='Validation error'),
    },
    description='Register a new user with email and password.',
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_success_headers(self, data):
        return {}

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        return response


@extend_schema(
    tags=['Authentication'],
    request=LoginSerializer,
    responses={
        200: TokenResponseSerializer,
        400: OpenApiResponse(description='Invalid credentials'),
    },
    description='Authenticate with email and password; receive JWT tokens.',
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from ..services.login_service import LoginService

        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        tokens = LoginService().issue_tokens(user=serializer.validated_data['user'])
        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    request=TokenRefreshRequestSerializer,
    responses={
        200: AccessTokenResponseSerializer,
        400: OpenApiResponse(description='Invalid or expired refresh token'),
    },
    description='Obtain a new access token using a valid refresh token.',
)
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'refresh': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)}, status=status.HTTP_200_OK)
        except (TokenError, InvalidToken) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    request=LogoutRequestSerializer,
    responses={
        204: OpenApiResponse(description='Logout successful'),
        400: DetailResponseSerializer,
    },
    description='Invalidate refresh token (server-side) by blacklisting it.',
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'refresh': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken):
            return Response({'detail': 'Invalid or expired refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Dashboard'],
    responses={200: DashboardSummarySerializer},
    description='Aggregated counts and recent activity for the current user, scoped by organization tenant.',
)
class DashboardSummaryView(CachedGETMixin, APIView):
    permission_classes = [IsAuthenticated]
    cache_namespace = NAMESPACE_DASHBOARD
    cache_path_suffix = '/api/v1/dashboard/summary/'

    def get(self, request, *args, **kwargs):
        cached = self.get_cached_response(request)
        if cached is not None:
            return cached

        user = request.user
        org_qs = organizations_queryset_for_user(user)

        org_ids = organization_ids_for_request(request)
        if org_ids:
            org_qs = org_qs.filter(pk__in=org_ids)

        total_projects = Project.objects.filter(
            project_visibility_q(user, org_ids),
            is_active=True,
        ).distinct().count()

        tasks_qs = Task.objects.filter(
            task_visibility_q(user, org_ids),
            project__is_active=True,
        ).distinct()
        total_tasks = tasks_qs.count()

        done_status_ids = completed_task_status_ids()
        completed_tasks = tasks_qs.filter(status_id__in=done_status_ids).count() if done_status_ids else 0
        pending_tasks = max(total_tasks - completed_tasks, 0)

        activity_cutoff = timezone.now() - timedelta(days=30)
        activity_base_qs = ActivityLog.objects.filter(
            created_at__gte=activity_cutoff,
            task__in=tasks_qs,
        )
        total_activity_logs = activity_base_qs.count()

        recent_activity_qs = activity_base_qs.select_related('task', 'user').order_by('-created_at')[:10]
        recent_activity = ActivityLogSerializer(recent_activity_qs, many=True).data

        activity_by_action_qs = (
            activity_base_qs
            .values('action')
            .annotate(value=Count('id'))
            .order_by('-value')[:20]
        )
        activity_by_action = [
            {'name': item['action'] or 'UNKNOWN', 'value': item['value']}
            for item in activity_by_action_qs
        ]

        payload = {
            'total_projects': total_projects,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'total_activity_logs': total_activity_logs,
            'recent_activity': recent_activity,
            'activity_by_action': activity_by_action,
        }

        response = Response(payload, status=status.HTTP_200_OK)
        return self.cache_response(request, response)


@extend_schema(
    tags=['Operations'],
    responses={
        200: HealthResponseSerializer,
        503: HealthResponseSerializer,
    },
    description='Public health check for load balancers and uptime monitoring.',
)
class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            db_ok = False

        groq_ok = False
        try:
            from apps.ai_assistant.services.groq_client import GroqClient

            groq_ok = GroqClient().is_configured()
        except Exception:
            groq_ok = False

        cache_ok = True
        try:
            cache.set('health:ping', '1', timeout=5)
            cache_ok = cache.get('health:ping') == '1'
        except Exception:
            cache_ok = False
        use_memory = getattr(settings, "RAG_FORCE_MEMORY_STORE", False)

        return Response(
            {
                'status': 'ok' if db_ok else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'database': 'ok' if db_ok else 'unavailable',
                'cache': 'locmem' if use_memory else (
    'redis' if settings.REDIS_AVAILABLE else 'locmem'
),

'vector_store': 'memory' if use_memory else (
    'redis' if settings.REDIS_AVAILABLE else 'memory'
),
                'groq_configured': groq_ok,
            },
            status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@extend_schema(
    tags=['Operations'],
    responses={200: MetricsResponseSerializer},
    description='Admin-only operational metrics for the platform.',
)
class MetricsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        cache_key = make_fixed_key(NAMESPACE_METRICS, 'platform')
        cached = get_cached_payload(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        payload = {
            'users': self._count_users(),
            'organizations': Organization.objects.count(),
            'workspaces': Workspace.objects.count(),
            'team_members': TeamMember.objects.count(),
            'organization_invites': OrganizationInvite.objects.count(),
            'projects': Project.objects.count(),
            'tasks': Task.objects.count(),
            'comments': Comment.objects.count(),
            'activity_logs': ActivityLog.objects.count(),
            'notifications': Notification.objects.count(),
        }

        set_cached_payload(cache_key, payload, timeout=get_metrics_cache_timeout())
        return Response(payload, status=status.HTTP_200_OK)

    def _count_users(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.count()


@extend_schema(
    tags=['Authentication'],
    request=ForgotPasswordSerializer,
    responses={200: DetailResponseSerializer},
    description='Request password reset. Always returns 200 regardless of whether the email exists (prevents user enumeration).',
)
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from apps.user_profiles.models import PasswordResetToken
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower().strip()
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
            reset_token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            try:
                from apps.core.tasks import send_password_reset_email
                send_password_reset_email.delay(user.pk, str(reset_token.token))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    "forgot-password: failed to queue send_password_reset_email for user %s — %s", user.pk, exc
                )
        except User.DoesNotExist:
            pass  # Silently ignore — prevents user enumeration
        return Response(
            {'detail': 'If that email is registered, a reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Authentication'],
    request=ResetPasswordSerializer,
    responses={
        200: DetailResponseSerializer,
        400: DetailResponseSerializer,
    },
    description='Reset password using a valid token. Token is immediately invalidated after use.',
)
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from apps.user_profiles.models import PasswordResetToken
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_value = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=token_value)
        except (PasswordResetToken.DoesNotExist, ValueError):
            return Response(
                {'detail': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if reset_token.is_used:
            return Response(
                {'detail': 'Token already used.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if reset_token.is_expired:
            return Response(
                {'detail': 'Token has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reset_token.user.set_password(new_password)
        reset_token.user.save()
        reset_token.is_used = True
        reset_token.save()
        return Response(
            {'detail': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK,
        )

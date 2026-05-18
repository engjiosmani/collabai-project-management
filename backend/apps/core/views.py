from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count
from django.db import connection
from django.utils import timezone

from common.workspace_access import workspaces_queryset_for_user
from apps.comments.models import ActivityLog
from apps.comments.models import Comment
from apps.comments.serializers import ActivityLogSerializer
from apps.notifications.models import Notification
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus
from apps.workspaces.models import Permission, Role, TeamMember, Workspace, WorkspaceInvite


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
        200: OpenApiResponse(description='JWT access and refresh tokens'),
        400: OpenApiResponse(description='Invalid credentials'),
    },
    description='Authenticate with email and password; receive JWT tokens.',
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from .services.login_service import LoginService
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        tokens = LoginService().issue_tokens(user=serializer.validated_data['user'])
        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
    responses={
        200: OpenApiResponse(description='New access token'),
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
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
    responses={
        204: OpenApiResponse(description='Logout successful'),
        400: OpenApiResponse(description='Invalid token or missing refresh token'),
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
    responses={200: OpenApiResponse(description='Aggregated dashboard summary')},
    description='Aggregated counts and recent activity for the current user (workspace-scoped).',
)
class DashboardSummaryView(APIView):
    """Return aggregated workspace-scoped counts and recent activity.

    Optimized to run a small number of DB queries and return cached-friendly,
    pre-aggregated metrics for dashboard consumption.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Workspaces the user can access (handles superuser)
        ws_qs = workspaces_queryset_for_user(user)

        # Projects accessible
        total_projects = Project.objects.filter(workspace__in=ws_qs).count()

        # Tasks accessible
        tasks_qs = Task.objects.filter(project__workspace__in=ws_qs)
        total_tasks = tasks_qs.count()

        # Determine "completed" statuses by name hints (case-insensitive).
        done_status_qs = TaskStatus.objects.filter(name__iregex=r"\b(done|completed|complete|closed|resolved|finished)\b")
        done_status_ids = list(done_status_qs.values_list('pk', flat=True))
        if done_status_ids:
            completed_tasks = tasks_qs.filter(status_id__in=done_status_ids).count()
        else:
            # Fallback: no status matches — treat completed as 0
            completed_tasks = 0

        pending_tasks = max(total_tasks - completed_tasks, 0)

        # Recent activity (limit 10) - fetch with select_related to avoid N+1
        recent_activity_qs = (
            ActivityLog.objects.filter(task__project__workspace__in=ws_qs)
            .select_related('task', 'user')
            .order_by('-created_at')[:10]
        )
        recent_activity = ActivityLogSerializer(recent_activity_qs, many=True).data

        # Activity aggregated by action (small aggregation)
        activity_by_action_qs = (
            ActivityLog.objects.filter(task__project__workspace__in=ws_qs)
            .values('action')
            .annotate(value=Count('id'))
            .order_by('-value')[:20]
        )
        activity_by_action = [
            {'name': a['action'] or 'UNKNOWN', 'value': a['value']} for a in activity_by_action_qs
        ]

        payload = {
            'total_projects': total_projects,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'recent_activity': recent_activity,
            'activity_by_action': activity_by_action,
        }

        return Response(payload, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Operations'],
    responses={200: OpenApiResponse(description='Service health')},
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

        return Response(
            {
                'status': 'ok' if db_ok else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'database': 'ok' if db_ok else 'unavailable',
            },
            status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@extend_schema(
    tags=['Operations'],
    responses={200: OpenApiResponse(description='Platform metrics')},
    description='Admin-only operational metrics for the platform.',
)
class MetricsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        payload = {
            'users': self._count_users(),
            'organizations': Organization.objects.count(),
            'workspaces': Workspace.objects.count(),
            'roles': Role.objects.count(),
            'permissions': Permission.objects.count(),
            'team_members': TeamMember.objects.count(),
            'workspace_invites': WorkspaceInvite.objects.count(),
            'projects': Project.objects.count(),
            'tasks': Task.objects.count(),
            'comments': Comment.objects.count(),
            'activity_logs': ActivityLog.objects.count(),
            'notifications': Notification.objects.count(),
        }
        return Response(payload, status=status.HTTP_200_OK)

    def _count_users(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.count()



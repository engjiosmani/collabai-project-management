from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from common.cache import CachedListMixin, NAMESPACE_ACTIVITY_LOGS, NAMESPACE_COMMENTS
from common.permissions import IsWorkspaceMemberCommentAuthorForWrite, IsWorkspaceTeamMember
from common.tenant_access import organization_ids_for_request
from common.role_permissions import task_visibility_q
from apps.tasks.models import Task
from ..filters import ActivityLogFilter, CommentFilter
from ..models import ActivityLog, Comment
from ..serializers import ActivityLogSerializer, CommentSerializer
from ..services.activity import log_comment_added


@extend_schema_view(
    list=extend_schema(tags=['Comments'], summary='List comments'),
    retrieve=extend_schema(tags=['Comments'], summary='Retrieve comment'),
    create=extend_schema(tags=['Comments'], summary='Create comment'),
    update=extend_schema(tags=['Comments'], summary='Update comment'),
    partial_update=extend_schema(tags=['Comments'], summary='Partially update comment'),
    destroy=extend_schema(tags=['Comments'], summary='Delete comment'),
)
class CommentViewSet(CachedListMixin, viewsets.ModelViewSet):
    cache_namespace = NAMESPACE_COMMENTS
    cache_default_list_path = '/api/v1/comments/'
    """
    CRUD for task comments. Workspace members may read; only the author may edit or delete.
    """

    serializer_class = CommentSerializer
    permission_classes = [IsWorkspaceMemberCommentAuthorForWrite]
    filterset_class = CommentFilter
    search_fields = (
        'content',
        'task__title',
        'task__project__name',
        'author__username',
        'author__email',
    )
    ordering_fields = (
        'created_at',
        'updated_at',
        'task__title',
        'author__username',
        'author__email',
    )
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[Comment]:
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()
        org_ids = organization_ids_for_request(self.request)
        return (
            Comment.objects.filter(
                task__in=Task.objects.filter(
                    task_visibility_q(self.request.user, org_ids),
                    project__is_active=True,
                )
            )
            .distinct()
            .select_related(
                'task',
                'task__project',
                'task__project__organization',
                'author',
            )
        )

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        log_comment_added(task=comment.task, user=self.request.user, content=comment.content)


@extend_schema_view(
    list=extend_schema(tags=['Activity logs'], summary='List activity logs'),
    retrieve=extend_schema(tags=['Activity logs'], summary='Retrieve activity log'),
)
class ActivityLogViewSet(CachedListMixin, viewsets.ReadOnlyModelViewSet):
    cache_namespace = NAMESPACE_ACTIVITY_LOGS
    cache_default_list_path = '/api/v1/activity-logs/'
    """Read-only activity entries for tasks in workspaces the user belongs to."""

    serializer_class = ActivityLogSerializer
    permission_classes = [IsWorkspaceTeamMember]
    filterset_class = ActivityLogFilter
    search_fields = (
        'action',
        'description',
        'task__title',
        'task__project__name',
        'user__username',
        'user__email',
    )
    ordering_fields = (
        'created_at',
        'updated_at',
        'action',
        'task__title',
        'user__username',
    )
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[ActivityLog]:
        if getattr(self, 'swagger_fake_view', False):
            return ActivityLog.objects.none()
        org_ids = organization_ids_for_request(self.request)

        days = self.request.query_params.get('days')
        if days is not None:
            try:
                days = int(days)
            except (ValueError, TypeError):
                days = 30
        else:
            days = 30

        cutoff = timezone.now() - timedelta(days=days)

        return (
            ActivityLog.objects.filter(
                created_at__gte=cutoff,
                task__in=Task.objects.filter(
                    task_visibility_q(self.request.user, org_ids),
                    project__is_active=True,
                )
            )
            .distinct()
            .select_related(
                'task',
                'task__project',
                'task__project__organization',
                'user',
            )
        )

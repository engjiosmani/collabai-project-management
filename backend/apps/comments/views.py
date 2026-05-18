from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from common.permissions import IsWorkspaceMemberCommentAuthorForWrite, IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

from .filters import ActivityLogFilter, CommentFilter
from .models import ActivityLog, Comment
from .serializers import ActivityLogSerializer, CommentSerializer


@extend_schema_view(
    list=extend_schema(tags=['Comments'], summary='List comments'),
    retrieve=extend_schema(tags=['Comments'], summary='Retrieve comment'),
    create=extend_schema(tags=['Comments'], summary='Create comment'),
    update=extend_schema(tags=['Comments'], summary='Update comment'),
    partial_update=extend_schema(tags=['Comments'], summary='Partially update comment'),
    destroy=extend_schema(tags=['Comments'], summary='Delete comment'),
)
class CommentViewSet(viewsets.ModelViewSet):
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
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            Comment.objects.filter(task__project__workspace_id__in=ws_ids)
            .select_related(
                'task',
                'task__project',
                'task__project__workspace',
                'task__project__workspace__organization',
                'author',
            )
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=['Activity logs'], summary='List activity logs'),
    retrieve=extend_schema(tags=['Activity logs'], summary='Retrieve activity log'),
)
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
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
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            ActivityLog.objects.filter(task__project__workspace_id__in=ws_ids)
            .select_related(
                'task',
                'task__project',
                'task__project__workspace',
                'task__project__workspace__organization',
                'user',
            )
        )
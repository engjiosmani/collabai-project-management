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
    search_fields = ('content',)
    ordering_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[Comment]:
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            Comment.objects.filter(task__project__workspace_id__in=ws_ids)
            .select_related('task', 'task__project', 'author')
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
    ordering_fields = ('created_at', 'updated_at', 'action')
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[ActivityLog]:
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            ActivityLog.objects.filter(task__project__workspace_id__in=ws_ids)
            .select_related('task', 'task__project', 'user')
        )
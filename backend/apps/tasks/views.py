from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from common.permissions import IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

from .filters import TaskFilter
from .models import Task
from .serializers import TaskSerializer


@extend_schema_view(
    list=extend_schema(tags=['Tasks'], summary='List tasks'),
    retrieve=extend_schema(tags=['Tasks'], summary='Retrieve task'),
    create=extend_schema(tags=['Tasks'], summary='Create task'),
    update=extend_schema(tags=['Tasks'], summary='Update task'),
    partial_update=extend_schema(tags=['Tasks'], summary='Partially update task'),
    destroy=extend_schema(tags=['Tasks'], summary='Delete task'),
)
class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD for tasks in projects belonging to the user's workspaces.
    Filter by project, workspace, organization, status, priority, assignee, dates.
    Sort with ordering=-created_at,priority,...
    """

    serializer_class = TaskSerializer
    permission_classes = [IsWorkspaceTeamMember]
    filterset_class = TaskFilter
    search_fields = ('title', 'description')
    ordering_fields = (
        'created_at',
        'updated_at',
        'title',
        'due_date',
        'status',
        'priority',
        'priority__level',
    )
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[Task]:
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            Task.objects.filter(project__workspace_id__in=ws_ids)
            .select_related('project', 'project__workspace', 'status', 'priority', 'assigned_to')
        )
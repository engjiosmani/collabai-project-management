from django.core.cache import cache
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.response import Response

from common.cache import make_list_key
from common.permissions import IsWorkspaceTeamMember
from common.role_permissions import (IsManagerOrAdmin)
from .filters import TaskFilter
from .models import Task, TaskStatus
from .serializers import TaskSerializer, TaskStatusSerializer

CACHE_NAMESPACE = 'tasks'
DEFAULT_TASK_STATUS_NAMES = ('To Do', 'In Progress', 'Done')


@extend_schema_view(
    list=extend_schema(tags=['Task statuses'], summary='List task statuses'),
    retrieve=extend_schema(tags=['Task statuses'], summary='Retrieve task status'),
)
class TaskStatusViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskStatusSerializer

    def get_queryset(self):
        if not TaskStatus.objects.exists():
            TaskStatus.objects.bulk_create(
                [TaskStatus(name=name) for name in DEFAULT_TASK_STATUS_NAMES],
                ignore_conflicts=True,
            )
        return TaskStatus.objects.all().order_by('name')


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

        workspace_ids = getattr(
            self.request,
            "workspace_ids",
            []
        )

        return (
            Task.objects.filter(
                project__workspace_id__in=workspace_ids
            )
            .select_related(
                'project',
                'project__workspace',
                'status',
                'priority',
                'assigned_to'
            )
        )

    def list(self, request, *args, **kwargs):
        cache_key = make_list_key(CACHE_NAMESPACE, request.user.pk, request.get_full_path())
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data)
        return response

    def get_permissions(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy"
        ]:
            return [IsManagerOrAdmin()]

        return super().get_permissions()

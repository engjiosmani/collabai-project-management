from copy import copy

from django.core.cache import cache
from django.db.models import Case, IntegerField, QuerySet, Value, When
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.response import Response

from apps.comments.services.activity import log_task_created, log_task_deleted, log_task_updated
from common.cache import make_list_key
from common.permissions import IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

from .filters import TaskFilter
from .models import Task, TaskStatus
from .serializers import TaskSerializer, TaskStatusSerializer

CACHE_NAMESPACE = 'tasks'
DEFAULT_TASK_STATUS_NAMES = ('To Do', 'In Progress', 'Done')
# Kanban column order (not alphabetical — "Done" must not appear before "To Do")
_TASK_STATUS_ORDER_CASE = Case(
    When(name='To Do', then=Value(0)),
    When(name='In Progress', then=Value(1)),
    When(name='Done', then=Value(2)),
    default=Value(99),
    output_field=IntegerField(),
)


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
        return TaskStatus.objects.annotate(
            _kb_order=_TASK_STATUS_ORDER_CASE,
        ).order_by('_kb_order', 'name')


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
    search_fields = (
        'title',
        'description',
        'status__name',
        'priority__name',
        'assigned_to__username',
        'assigned_to__email',
        'project__name',
        'project__workspace__name',
        'task_labels__label__name',
    )
    ordering_fields = (
        'created_at',
        'updated_at',
        'title',
        'due_date',
        'status',
        'status__name',
        'priority',
        'priority__name',
        'priority__level',
        'assigned_to__username',
        'assigned_to__email',
        'project__name',
    )
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[Task]:
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()

        workspace_ids = getattr(self.request, 'workspace_ids', [])

        return (
            Task.objects.filter(project__workspace_id__in=workspace_ids)
            .select_related(
                'project',
                'project__workspace',
                'project__workspace__organization',
                'status',
                'priority',
                'assigned_to',
            )
            .prefetch_related('task_labels__label')
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.request.query_params.get('search') or self.request.query_params.get('label'):
            queryset = queryset.distinct()
        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = make_list_key(CACHE_NAMESPACE, request.user.pk, request.get_full_path())
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data)
        return response

    def perform_create(self, serializer):
        task = serializer.save()
        log_task_created(task=task, user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        previous = copy(instance)
        if previous.status_id:
            previous.status  # populate cache
        if previous.priority_id:
            previous.priority
        if previous.assigned_to_id:
            previous.assigned_to
        task = serializer.save()
        log_task_updated(task=task, user=self.request.user, previous=previous)

    def perform_destroy(self, instance):
        log_task_deleted(task=instance, user=self.request.user)

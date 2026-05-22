from copy import copy

from django.db.models import Case, IntegerField, QuerySet, Value, When
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from apps.comments.services.activity import log_task_created, log_task_deleted, log_task_updated
from apps.projects.models import ProjectMember
from common.cache import CachedListMixin, NAMESPACE_TASKS
from common.cache_signals import invalidate_after_task_change
from common.permissions import IsWorkspaceTeamMember
from common.role_permissions import (
    task_visibility_q,
    user_can_assign_task,
    user_can_update_task,
    user_is_manager_or_above,
)
from .filters import TaskFilter
from .models import Task, TaskStatus
from .serializers import TaskSerializer, TaskStatusSerializer

DEFAULT_LIST_PATH = '/api/v1/tasks/'
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
class TaskViewSet(CachedListMixin, viewsets.ModelViewSet):
    cache_namespace = NAMESPACE_TASKS
    cache_default_list_path = DEFAULT_LIST_PATH
    """
    CRUD for tasks in projects belonging to the user's organizations.
    Filter by project, organization, status, priority, assignee, dates.
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
        'project__organization__name',
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

        org_ids = getattr(self.request, 'organization_ids', [])

        return (
            Task.objects.filter(
                task_visibility_q(self.request.user, org_ids),
                project__is_active=True,
            )
            .distinct()
            .select_related(
                'project',
                'project__organization',
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

    def _invalidate_task_list_cache(self) -> None:
        self.invalidate_list_cache_for_request()
        invalidate_after_task_change()

    def _require_manager_or_above(self, project) -> None:
        if not user_is_manager_or_above(self.request.user, project.organization):
            raise PermissionDenied('You must be a manager or above to modify tasks.')

    def _validate_task_update_permissions(self, instance, validated_data) -> None:
        project = validated_data.get('project') or instance.project
        if user_is_manager_or_above(self.request.user, project.organization):
            return

        if not user_can_update_task(self.request.user, instance):
            raise PermissionDenied('You can only update tasks assigned to you.')

        allowed_member_fields = {'status', 'description'}
        requested_fields = set(validated_data.keys())
        if not requested_fields.issubset(allowed_member_fields):
            raise PermissionDenied(
                'Members can only update status and description on assigned tasks.'
            )

    def destroy(self, request, *args, **kwargs):
        self._require_manager_or_above(self.get_object().project)
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:
            self._invalidate_task_list_cache()
        return response

    def perform_create(self, serializer):
        self._require_manager_or_above(serializer.validated_data['project'])
        assigned_to = serializer.validated_data.get('assigned_to')
        if assigned_to and not user_can_assign_task(
            self.request.user,
            serializer.validated_data['project'].organization,
        ):
            raise PermissionDenied('You do not have permission to assign tasks.')
        task = serializer.save()
        if task.assigned_to_id:
            ProjectMember.objects.get_or_create(project=task.project, user=task.assigned_to)
        log_task_created(task=task, user=self.request.user)
        self._invalidate_task_list_cache()

    def perform_update(self, serializer):
        instance = serializer.instance
        project = serializer.validated_data.get('project') or instance.project
        self._validate_task_update_permissions(instance, serializer.validated_data)
        previous = copy(instance)
        if previous.status_id:
            previous.status  # populate cache
        if previous.priority_id:
            previous.priority
        if previous.assigned_to_id:
            previous.assigned_to
        task = serializer.save()
        if task.assigned_to_id:
            ProjectMember.objects.get_or_create(project=task.project, user=task.assigned_to)
        log_task_updated(task=task, user=self.request.user, previous=previous)
        self._invalidate_task_list_cache()

    def perform_destroy(self, instance):
        log_task_deleted(task=instance, user=self.request.user)
        super().perform_destroy(instance)

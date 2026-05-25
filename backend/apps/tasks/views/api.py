from copy import copy

from django.http import FileResponse
from django.db.models import Case, IntegerField, Prefetch, QuerySet, Value, When
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.comments.models import ActivityLog
from apps.comments.services.activity import log_task_created, log_task_deleted, log_task_updated
from apps.projects.models import ProjectMember
from common.cache import CachedListMixin, NAMESPACE_TASKS
from common.cache_signals import invalidate_after_task_change
from common.permissions import IsWorkspaceTeamMember
from common.tenant_access import organization_ids_for_request
from common.role_permissions import (
    task_visibility_q,
    user_can_assign_task_in_project,
    user_can_manage_project,
    user_can_update_task,
)
from ..filters import TaskFilter
from ..models import Attachment, Task, TaskPriority, TaskStatus
from ..serializers import (
    TaskAttachmentSerializer,
    TaskAttachmentUploadSerializer,
    TaskPrioritySerializer,
    TaskSerializer,
    TaskStatusSerializer,
)

DEFAULT_LIST_PATH = '/api/v1/tasks/'
DEFAULT_TASK_STATUS_NAMES = ('To Do', 'In Progress', 'Done')
DEFAULT_TASK_PRIORITY_VALUES = (
    ('Low', 1),
    ('Medium', 2),
    ('High', 3),
    ('Urgent', 4),
)
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
    list=extend_schema(tags=['Task priorities'], summary='List task priorities'),
    retrieve=extend_schema(tags=['Task priorities'], summary='Retrieve task priority'),
)
class TaskPriorityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskPrioritySerializer

    def get_queryset(self):
        if not TaskPriority.objects.exists():
            TaskPriority.objects.bulk_create(
                [TaskPriority(name=name, level=level) for name, level in DEFAULT_TASK_PRIORITY_VALUES],
                ignore_conflicts=True,
            )
        return TaskPriority.objects.order_by('level', 'name')


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

        org_ids = organization_ids_for_request(self.request)

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
            .prefetch_related(
                Prefetch(
                    'activity_logs',
                    queryset=ActivityLog.objects.filter(action='Task created').select_related('user').order_by('created_at'),
                    to_attr='task_created_logs',
                )
            )
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.request.query_params.get('search') or self.request.query_params.get('label'):
            queryset = queryset.distinct()
        return queryset

    def _invalidate_task_list_cache(self) -> None:
        self.invalidate_list_cache_for_request()
        invalidate_after_task_change()

    def _user_can_delete_task(self, user, task: Task) -> bool:
        if user_can_manage_project(user, task.project):
            return True

        return ActivityLog.objects.filter(
            task=task,
            action='Task created',
            user=user,
        ).exists()

    def _require_manager_or_above(self, project) -> None:
        if not user_can_manage_project(self.request.user, project):
            raise PermissionDenied('You must be a manager or above to modify tasks.')

    def _validate_task_update_permissions(self, instance, validated_data) -> None:
        project = validated_data.get('project') or instance.project
        if user_can_manage_project(self.request.user, project):
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
        task = self.get_object()
        if not self._user_can_delete_task(request.user, task):
            raise PermissionDenied('You must be a manager, admin, or the task creator to delete this task.')
        self.perform_destroy(task)
        self._invalidate_task_list_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        self._require_manager_or_above(serializer.validated_data['project'])
        assigned_to = serializer.validated_data.get('assigned_to')
        if assigned_to and not user_can_assign_task_in_project(
            self.request.user,
            serializer.validated_data['project'],
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

    @action(detail=True, methods=['get', 'post'], url_path='attachments')
    def attachments(self, request, pk=None):
        task = self.get_object()

        if request.method == 'GET':
            attachments = task.attachments.select_related('uploaded_by').order_by('-created_at')
            return Response(
                TaskAttachmentSerializer(attachments, many=True, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )

        if not (user_can_update_task(request.user, task) or user_can_manage_project(request.user, task.project)):
            raise PermissionDenied('You do not have permission to upload attachments for this task.')

        serializer = TaskAttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_obj = serializer.validated_data['file']
        attachment = Attachment.objects.create(
            task=task,
            uploaded_by=request.user,
            file=file_obj,
            file_name=file_obj.name,
        )
        return Response(
            TaskAttachmentSerializer(attachment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Tasks'],
        summary='Download task attachment',
        parameters=[OpenApiParameter('attachment_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={200: bytes},
    )
    @action(detail=True, methods=['get'], url_path=r'attachments/(?P<attachment_id>[^/.]+)/download', url_name='attachment-download')
    def download_attachment(self, request, pk=None, attachment_id=None):
        task = self.get_object()
        attachment = get_object_or_404(task.attachments.select_related('uploaded_by'), pk=attachment_id)
        attachment.file.open('rb')
        return FileResponse(attachment.file, as_attachment=True, filename=attachment.file_name)

    @extend_schema(
        tags=['Tasks'],
        summary='Delete task attachment',
        parameters=[OpenApiParameter('attachment_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={204: None},
    )
    @action(detail=True, methods=['delete'], url_path=r'attachments/(?P<attachment_id>[^/.]+)', url_name='attachment-detail')
    def delete_attachment(self, request, pk=None, attachment_id=None):
        task = self.get_object()
        attachment = get_object_or_404(task.attachments.select_related('uploaded_by'), pk=attachment_id)

        if not (
            user_can_manage_project(request.user, task.project)
            or attachment.uploaded_by_id == request.user.id
        ):
            raise PermissionDenied('You do not have permission to delete this attachment.')

        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

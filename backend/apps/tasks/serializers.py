from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.comments.models import ActivityLog
from apps.projects.models import Project
from common.role_permissions import user_has_project_access, user_is_manager_or_above
from common.tenant_access import user_can_access_organization

from .models import Attachment, Label, Task, TaskLabel, TaskPriority, TaskStatus


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ('id', 'name')


class TaskPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskPriority
        fields = ('id', 'name', 'level')


class TaskLabelsField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        task = value
        task_labels = getattr(task, 'task_labels', None)
        labels = task_labels.all() if task_labels is not None else TaskLabel.objects.filter(task=task).select_related('label')
        return [
            {
                'id': task_label.label_id,
                'name': task_label.label.name,
                'color': task_label.label.color,
            }
            for task_label in labels
            if task_label.label_id and task_label.label
        ]

    def to_internal_value(self, data):
        if data in (None, '', []):
            return []

        if isinstance(data, str):
            raw_items = [item.strip() for item in data.split(',')]
        elif isinstance(data, list):
            raw_items = data
        else:
            raise serializers.ValidationError('Labels must be a list or comma-separated string.')

        labels: list[str] = []
        seen: set[str] = set()

        for item in raw_items:
            if isinstance(item, dict):
                value = item.get('name') or item.get('label') or item.get('value')
            else:
                value = item

            text = str(value or '').strip()
            if not text:
                continue

            normalized = text.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            labels.append(text)

        return labels


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            'id',
            'task',
            'uploaded_by',
            'uploaded_by_email',
            'file_name',
            'file',
            'file_url',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'task',
            'uploaded_by',
            'uploaded_by_email',
            'file_name',
            'file_url',
            'created_at',
            'updated_at',
        )

    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        url = reverse(
            'task-attachment-download',
            kwargs={'pk': obj.task_id, 'attachment_id': obj.pk},
        )
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class TaskAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class TaskSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    labels = TaskLabelsField(required=False)
    created_by_id = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id',
            'project',
            'title',
            'description',
            'status',
            'status_name',
            'priority',
            'priority_name',
            'assigned_to',
            'assigned_to_email',
            'due_date',
            'labels',
            'created_by_id',
            'created_by_email',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_created_by_id(self, obj):
        creator = self._get_creator_activity(obj)
        return creator.user_id if creator and creator.user_id else None

    def get_created_by_email(self, obj):
        creator = self._get_creator_activity(obj)
        if creator and creator.user:
            return creator.user.email or creator.user.get_username()
        return None

    def _get_creator_activity(self, obj):
        cached = getattr(obj, 'task_created_logs', None)
        if cached:
            return cached[0]

        return (
            ActivityLog.objects.filter(task=obj, action='Task created')
            .select_related('user')
            .order_by('created_at')
            .first()
        )

    def _sync_labels(self, task: Task, label_names: list[str]) -> None:
        if label_names is None:
            return

        normalized_labels = []
        for name in label_names:
            label = Label.objects.filter(name__iexact=name).first()
            if label is None:
                label = Label.objects.create(name=name)
            normalized_labels.append(label)

        TaskLabel.objects.filter(task=task).exclude(label__in=normalized_labels).delete()

        existing_label_ids = set(TaskLabel.objects.filter(task=task).values_list('label_id', flat=True))
        for label in normalized_labels:
            if label.id not in existing_label_ids:
                TaskLabel.objects.create(task=task, label=label)

    def create(self, validated_data):
        label_names = validated_data.pop('labels', None)
        task = super().create(validated_data)
        if label_names is not None:
            self._sync_labels(task, label_names)
        return task

    def update(self, instance, validated_data):
        label_names = validated_data.pop('labels', serializers.empty)
        task = super().update(instance, validated_data)
        if label_names is not serializers.empty:
            self._sync_labels(task, label_names)
        return task

    def validate_project(self, value: Project):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not value.is_active:
            raise serializers.ValidationError('Invalid project or access denied.')
        if not user_has_project_access(user, value) and not user_is_manager_or_above(
            user,
            value.organization,
        ):
            raise serializers.ValidationError('Invalid project or access denied.')
        return value

    def validate(self, attrs):
        project = attrs.get('project')
        if project is None and self.instance:
            project = self.instance.project

        assigned = attrs.get('assigned_to')
        if assigned is None and self.instance:
            assigned = self.instance.assigned_to
        if assigned is not None and project is not None:
            if not user_can_access_organization(assigned, project.organization):
                raise serializers.ValidationError(
                    {'assigned_to': 'Assignee must be a member of the project organization.'}
                )

        return attrs

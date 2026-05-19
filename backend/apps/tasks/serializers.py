from rest_framework import serializers

from apps.projects.models import Project
from common.tenant_access import user_can_access_organization

from .models import Task, TaskStatus


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ('id', 'name')


class TaskSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)

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
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_project(self, value: Project):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_organization(user, value.organization):
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
from rest_framework import serializers

from apps.projects.models import Project
from common.workspace_access import user_can_access_workspace

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id',
            'project',
            'title',
            'description',
            'status',
            'priority',
            'assigned_to',
            'due_date',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_project(self, value: Project):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_workspace(user, value.workspace):
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
            if not user_can_access_workspace(assigned, project.workspace):
                raise serializers.ValidationError(
                    {'assigned_to': 'Assignee must be a member of the project workspace.'}
                )

        return attrs
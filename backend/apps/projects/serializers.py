from django.db import IntegrityError
from rest_framework import serializers

from apps.workspaces.models import Workspace
from common.workspace_access import user_can_access_workspace

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    organization_name = serializers.CharField(source='workspace.organization.name', read_only=True)

    class Meta:
        model = Project
        fields = (
            'id',
            'workspace',
            'workspace_name',
            'organization_name',
            'name',
            'description',
            'start_date',
            'due_date',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_workspace(self, value: Workspace):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_workspace(user, value):
            raise serializers.ValidationError('Invalid workspace or you are not a member of this workspace.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date')
        due = attrs.get('due_date')
        if start and due and due < start:
            raise serializers.ValidationError({'due_date': 'Due date cannot be before start date.'})
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {'name': 'A project with this name already exists in the workspace.'}
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {'name': 'A project with this name already exists in the workspace.'}
            )
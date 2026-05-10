from rest_framework import serializers

from apps.tasks.models import Task
from common.workspace_access import user_can_access_workspace

from .models import ActivityLog, Comment


class CommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source='author.email', read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id',
            'task',
            'author',
            'author_email',
            'content',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('author', 'created_at', 'updated_at')

    def validate_content(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def validate_task(self, value: Task):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        workspace = value.project.workspace
        if not user_can_access_workspace(user, workspace):
            raise serializers.ValidationError('Invalid task or access denied.')
        return value


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = (
            'id',
            'task',
            'user',
            'action',
            'description',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
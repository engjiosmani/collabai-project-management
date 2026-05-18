from rest_framework import serializers

from apps.workspaces.models import Workspace

from .models import AIRequest


class RAGQuerySerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()
    question = serializers.CharField(max_length=4000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    task_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_workspace_id(self, value):
        if not Workspace.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Workspace not found.')
        return value


class RAGSearchSerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()
    query = serializers.CharField(max_length=2000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)

    def validate_workspace_id(self, value):
        if not Workspace.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Workspace not found.')
        return value


class ReindexSerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()

    def validate_workspace_id(self, value):
        if not Workspace.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Workspace not found.')
        return value


class AIRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequest
        fields = ('id', 'prompt', 'response', 'status', 'task', 'created_at')
        read_only_fields = fields

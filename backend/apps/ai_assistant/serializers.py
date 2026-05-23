from rest_framework import serializers

from apps.organizations.models import Organization

from .models import AIRequest


class RAGQuerySerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    question = serializers.CharField(max_length=4000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    task_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_organization_id(self, value):
        if not Organization.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Organization not found.')
        return value


class RAGSearchSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    query = serializers.CharField(max_length=2000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)

    def validate_organization_id(self, value):
        if not Organization.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Organization not found.')
        return value


class ReindexSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()

    def validate_organization_id(self, value):
        if not Organization.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Organization not found.')
        return value


class TextAnalyzeSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=16000)
    mode = serializers.ChoiceField(
        choices=('summary', 'action_items', 'sentiment'),
        default='summary',
    )
    task_id = serializers.IntegerField(required=False, allow_null=True)


class TextAnalyzeResponseSerializer(serializers.Serializer):
    mode = serializers.CharField()
    result = serializers.CharField()
    request_id = serializers.IntegerField()


class AIRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequest
        fields = ('id', 'organization', 'prompt', 'response', 'status', 'task', 'created_at')
        read_only_fields = fields

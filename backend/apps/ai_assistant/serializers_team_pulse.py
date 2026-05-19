from rest_framework import serializers

from .models import GitHubWorkspaceConfig, TeamPulseAlert, TeamPulseReport


class GitHubWorkspaceConfigSerializer(serializers.ModelSerializer):
    has_token = serializers.SerializerMethodField()

    class Meta:
        model = GitHubWorkspaceConfig
        fields = (
            'workspace',
            'repos',
            'member_github_logins',
            'is_enabled',
            'has_token',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('workspace', 'has_token', 'created_at', 'updated_at')

    def get_has_token(self, obj) -> bool:
        return bool(obj.access_token)

    def create(self, validated_data):
        token = self.context['request'].data.get('access_token', '')
        instance, _ = GitHubWorkspaceConfig.objects.update_or_create(
            workspace=validated_data['workspace'],
            defaults={
                'repos': validated_data.get('repos', []),
                'member_github_logins': validated_data.get('member_github_logins', {}),
                'is_enabled': validated_data.get('is_enabled', False),
            },
        )
        if token:
            instance.access_token = token
            instance.save(update_fields=['access_token', 'updated_at'])
        return instance

    def update(self, instance, validated_data):
        token = self.context['request'].data.get('access_token')
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if token:
            instance.access_token = token
        instance.save()
        return instance


class GitHubWorkspaceConfigWriteSerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()
    access_token = serializers.CharField(required=False, allow_blank=True)
    repos = serializers.ListField(child=serializers.CharField(), required=False)
    member_github_logins = serializers.DictField(
        child=serializers.CharField(),
        required=False,
    )
    is_enabled = serializers.BooleanField(required=False, default=False)


class TeamPulseAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    related_user_email = serializers.EmailField(source='related_user.email', read_only=True)

    class Meta:
        model = TeamPulseAlert
        fields = (
            'id',
            'workspace',
            'user',
            'user_email',
            'related_user',
            'related_user_email',
            'alert_type',
            'severity',
            'title',
            'message',
            'metrics',
            'is_dismissed',
            'created_at',
        )
        read_only_fields = fields


class TeamPulseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamPulseReport
        fields = (
            'id',
            'workspace',
            'report_type',
            'summary_markdown',
            'payload',
            'period_start',
            'period_end',
            'created_at',
        )
        read_only_fields = fields


class TeamPulseRunSerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()
    run_type = serializers.ChoiceField(choices=['workload', 'standup', 'both'])

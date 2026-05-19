from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from .models import GitHubOrganizationConfig, TeamPulseAlert, TeamPulseReport


class GitHubOrganizationConfigSerializer(serializers.ModelSerializer):
    has_token = serializers.SerializerMethodField()

    class Meta:
        model = GitHubOrganizationConfig
        fields = (
            'organization',
            'repos',
            'member_github_logins',
            'is_enabled',
            'has_token',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('organization', 'has_token', 'created_at', 'updated_at')

    def get_has_token(self, obj) -> bool:
        return bool(obj.access_token)


class GitHubOrganizationConfigWriteSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
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
            'organization',
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
            'organization',
            'report_type',
            'summary_markdown',
            'payload',
            'period_start',
            'period_end',
            'created_at',
        )
        read_only_fields = fields


class TeamPulseRunSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    run_type = serializers.ChoiceField(choices=['standup'], default='standup')


@extend_schema_serializer(component_name='TeamPulseDetailResponse')
class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class TeamPulseOverviewSerializer(serializers.Serializer):
    github = GitHubOrganizationConfigSerializer(allow_null=True)
    latest_standup = TeamPulseReportSerializer(allow_null=True)


class TeamPulseRunQueuedSerializer(serializers.Serializer):
    standup = serializers.CharField()


class TeamPulseRunResponseSerializer(serializers.Serializer):
    standup = TeamPulseReportSerializer()

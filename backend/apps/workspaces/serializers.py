from django.db import IntegrityError
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.organizations.models import Organization
from common.tenant_access import user_can_access_organization

from .models import JobRole, TeamMember, Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = (
            'id',
            'organization',
            'organization_name',
            'name',
            'is_active',
            'member_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'member_count',
            'created_at',
            'updated_at',
        )

    def validate_organization(self, value: Organization):
        """Validate user has access to the selected organization."""
        if value is None:
            raise serializers.ValidationError('This field is required.')

        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        if user and not user_can_access_organization(user, value):
            raise serializers.ValidationError(
                'Invalid organization or you are not a member of this organization.'
            )
        return value

    def validate_name(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def validate(self, attrs):
        name = attrs.get('name')
        organization = attrs.get('organization')

        if self.instance is not None:
            name = name if name is not None else self.instance.name
            organization = organization if organization is not None else self.instance.organization

        if name and organization:
            qs = Workspace.objects.filter(
                organization=organization,
                name__iexact=name
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    'name': 'A workspace with this name already exists in the organization.'
                })

        return attrs

    def create(self, validated_data):
        try:
            workspace = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'name': 'A workspace with this name already exists in the organization.'
            })

        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            TeamMember.objects.get_or_create(
                workspace=workspace,
                user=request.user,
                defaults={'role': TeamMember.WORKSPACE_ADMIN}
            )

        return workspace

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'name': 'A workspace with this name already exists in the organization.'
            })


class JobRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRole
        fields = (
            'id',
            'code',
            'name',
            'description',
            'task_categories',
            'is_active',
        )
        read_only_fields = fields


@extend_schema_serializer(component_name='WorkspaceTeamMember')
class TeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    job_role_name = serializers.CharField(source='job_role.name', read_only=True, allow_null=True)
    job_role_code = serializers.CharField(source='job_role.code', read_only=True, allow_null=True)
    task_categories = serializers.SerializerMethodField()
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    def get_task_categories(self, obj):
        if obj.job_role_id and obj.job_role:
            return list(obj.job_role.task_categories or [])
        return []

    class Meta:
        model = TeamMember
        fields = (
            'id',
            'workspace',
            'workspace_name',
            'user',
            'user_email',
            'role',
            'job_role',
            'job_role_name',
            'job_role_code',
            'task_categories',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'workspace',
            'workspace_name',
            'user',
            'user_email',
            'job_role_name',
            'job_role_code',
            'task_categories',
            'created_at',
            'updated_at',
        )


class TeamMemberJobRoleUpdateSerializer(serializers.Serializer):
    job_role_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_job_role_id(self, value):
        if value is None:
            return None

        if not JobRole.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('Job role not found.')

        return value

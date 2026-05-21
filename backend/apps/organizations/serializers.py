from django.db import IntegrityError
from rest_framework import serializers
from apps.workspaces.models import Workspace, TeamMember

from apps.workspaces.models import JobRole, Workspace, TeamMember
from .models import Organization, OrganizationInvite, OrganizationMember



class OrganizationSerializer(serializers.ModelSerializer):
    project_count = serializers.IntegerField(read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = (
            'id',
            'name',
            'description',
            'project_count',
            'member_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('project_count', 'member_count', 'created_at', 'updated_at')

    def validate_name(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        qs = Organization.objects.filter(name__iexact=text)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An organization with this name already exists.')
        return text

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'An organization with this name already exists.'})

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'An organization with this name already exists.'})


class OrganizationMemberJobRoleUpdateSerializer(serializers.Serializer):
    job_role_id = serializers.IntegerField(required=False, allow_null=True)


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    job_role_id = serializers.IntegerField(source='job_role.id', read_only=True, allow_null=True)
    job_role_code = serializers.CharField(source='job_role.code', read_only=True, allow_null=True)
    job_role_name = serializers.CharField(source='job_role.name', read_only=True, allow_null=True)

    class Meta:
        model = OrganizationMember
        fields = (
            'id',
            'organization',
            'user_id',
            'username',
            'email',
            'role',
            'job_role_id',
            'job_role_code',
            'job_role_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class OrganizationInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationInvite.ROLE_CHOICES,
        default=OrganizationInvite.MEMBER,
    )
    workspace_id = serializers.IntegerField(required=False, allow_null=True)

class OrganizationInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvite
        fields = (
            'id',
            'organization',
            'workspace',
            'email',
            'role',
            'token',
            'is_accepted',
            'expires_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

class OrgMemberRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=OrganizationMember.ROLE_CHOICES)
    job_role_id = serializers.IntegerField(required=False, allow_null=True)

class WorkspaceInOrgSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)
    class Meta:
        model = Workspace
        fields = ('id', 'name', 'is_active', 'member_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'member_count', 'created_at', 'updated_at')

class TeamMemberInOrgSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    job_role_name = serializers.CharField(source='job_role.name', read_only=True, allow_null=True)
    class Meta:
        model = TeamMember
        fields = ('id', 'user_id', 'username', 'email', 'role', 'job_role_name', 'created_at', 'updated_at')
        read_only_fields = fields

class AddWorkspaceMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=TeamMember.ROLE_CHOICES,
        default=TeamMember.MEMBER,
    )

class WorkspaceMemberRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=TeamMember.ROLE_CHOICES)
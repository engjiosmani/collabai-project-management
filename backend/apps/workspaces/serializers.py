from django.db import IntegrityError
from django.utils.crypto import get_random_string
from rest_framework import serializers

from apps.organizations.models import Organization
from common.workspace_access import user_can_access_workspace

from .models import Permission, Role, TeamMember, Workspace, WorkspaceInvite


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'code', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate_code(self, value: str):
        text = (value or '').strip().lower()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        qs = Permission.objects.filter(code__iexact=text)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A permission with this code already exists.')
        return text

    def validate_name(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'code': 'A permission with this code already exists.'})

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'code': 'A permission with this code already exists.'})


class WorkspaceSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    role_count = serializers.IntegerField(read_only=True)
    invite_count = serializers.IntegerField(read_only=True)
    project_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = (
            'id',
            'organization',
            'organization_name',
            'name',
            'is_active',
            'member_count',
            'role_count',
            'invite_count',
            'project_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('member_count', 'role_count', 'invite_count', 'project_count', 'created_at', 'updated_at')

    def validate_organization(self, value: Organization):
        if value is None:
            raise serializers.ValidationError('This field is required.')
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
            qs = Workspace.objects.filter(organization=organization, name__iexact=name)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'name': 'A workspace with this name already exists in the organization.'})
        return attrs

    def create(self, validated_data):
        try:
            workspace = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'A workspace with this name already exists in the organization.'})

        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            TeamMember.objects.get_or_create(workspace=workspace, user=request.user)
        return workspace

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'A workspace with this name already exists in the organization.'})


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        required=False,
        default=list,
    )
    permission_codes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = ('id', 'workspace', 'name', 'permissions', 'permission_codes', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def get_permission_codes(self, obj) -> list[str]:
        return [permission.code for permission in obj.permissions.all()]

    def validate_workspace(self, value: Workspace):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_workspace(user, value):
            raise serializers.ValidationError('Invalid workspace or you are not a member of this workspace.')
        return value

    def validate_name(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def validate(self, attrs):
        workspace = attrs.get('workspace') or getattr(self.instance, 'workspace', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if workspace and name:
            qs = Role.objects.filter(workspace=workspace, name__iexact=name)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'name': 'A role with this name already exists in the workspace.'})
        return attrs

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        try:
            role = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'A role with this name already exists in the workspace.'})
        role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        try:
            role = super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'A role with this name already exists in the workspace.'})
        if permissions is not None:
            role.permissions.set(permissions)
        return role


class TeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = TeamMember
        fields = (
            'id',
            'workspace',
            'workspace_name',
            'user',
            'user_email',
            'role',
            'role_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class WorkspaceInviteSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = WorkspaceInvite
        fields = (
            'id',
            'workspace',
            'workspace_name',
            'email',
            'role',
            'role_name',
            'token',
            'is_accepted',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('token', 'is_accepted', 'created_at', 'updated_at')

    def validate_workspace(self, value: Workspace):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_workspace(user, value):
            raise serializers.ValidationError('Invalid workspace or you are not a member of this workspace.')
        return value

    def validate_email(self, value: str):
        text = (value or '').strip().lower()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def validate(self, attrs):
        workspace = attrs.get('workspace') or getattr(self.instance, 'workspace', None)
        role = attrs.get('role') if 'role' in attrs else getattr(self.instance, 'role', None)
        if role is not None and workspace is not None and role.workspace_id != workspace.id:
            raise serializers.ValidationError({'role': 'Invite role must belong to the same workspace.'})
        return attrs

    def create(self, validated_data):
        validated_data.setdefault('token', get_random_string(32))
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'email': 'An invite for this email already exists in the workspace.'})







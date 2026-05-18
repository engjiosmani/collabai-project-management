from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.workspaces.models import Role, Workspace
from common.workspace_access import user_can_access_workspace

from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = Profile
        fields = (
            'id',
            'workspace',
            'workspace_name',
            'role',
            'role_name',
            'bio',
            'phone_number',
            'avatar',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'date_joined',
            'profile',
        )
        read_only_fields = fields

    def get_profile(self, obj) -> dict | None:
        try:
            profile = obj.profile
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            return None
        return ProfileSerializer(profile, context=self.context).data


class UserMeSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    workspace = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Workspace.objects.all())
    role = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Role.objects.all())

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'bio', 'phone_number', 'workspace', 'role')

    def validate_workspace(self, value: Workspace):
        user = self.instance or getattr(self.context.get('request'), 'user', None)
        if value is not None and not user_can_access_workspace(user, value):
            raise serializers.ValidationError('Invalid workspace or you are not a member of this workspace.')
        return value

    def validate(self, attrs):
        workspace = attrs.get('workspace')
        role = attrs.get('role')
        try:
            existing_profile = self.instance.profile
        except Profile.DoesNotExist:
            existing_profile = None
        if role is not None and workspace is None:
            workspace = getattr(existing_profile, 'workspace', None)
        if role is not None and workspace is None:
            raise serializers.ValidationError({'workspace': 'Workspace is required when selecting a role.'})
        if role is not None and workspace is not None and role.workspace_id != workspace.id:
            raise serializers.ValidationError({'role': 'Role must belong to the selected workspace.'})
        return attrs

    def update(self, instance, validated_data):
        profile, _ = Profile.objects.get_or_create(user=instance)
        for attr in ('email', 'first_name', 'last_name'):
            if attr in validated_data:
                setattr(instance, attr, validated_data.pop(attr))
        for attr in ('bio', 'phone_number', 'workspace', 'role'):
            if attr in validated_data:
                setattr(profile, attr, validated_data.pop(attr))
        instance.save()
        profile.save()
        return instance





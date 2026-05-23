from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.organizations.models import Organization
from common.tenant_access import user_can_access_organization

from ..models import Project, ProjectMember

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = (
            'id',
            'project',
            'user',
            'user_email',
            'user_username',
            'user_full_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_user_full_name(self, obj) -> str:
        u = obj.user
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.username or u.email


class AddProjectMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        user = User.objects.filter(pk=value).first()
        if user is None:
            raise serializers.ValidationError('User not found.')
        project = self.context.get('project')
        if project is not None and not user_can_access_organization(user, project.organization):
            raise serializers.ValidationError(
                'User must be a member of this project organization.'
            )
        return value


class ProjectSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id',
            'organization',
            'organization_name',
            'name',
            'description',
            'start_date',
            'due_date',
            'is_active',
            'member_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at', 'member_count')

    def get_member_count(self, obj) -> int:
        return obj.members.count()

    def validate_organization(self, value: Organization):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user_can_access_organization(user, value):
            raise serializers.ValidationError(
                'Invalid organization or you are not a member of this organization.'
            )
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
                {'name': 'A project with this name already exists in this organization.'}
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {'name': 'A project with this name already exists in this organization.'}
            )

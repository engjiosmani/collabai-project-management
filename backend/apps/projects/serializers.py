from django.db import IntegrityError
from rest_framework import serializers

from apps.organizations.models import Organization
from common.tenant_access import user_can_access_organization

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

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
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

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

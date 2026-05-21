from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models import Organization
from common.tenant_access import user_can_access_organization

from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)

    class Meta:
        model = Profile
        fields = (
            'id',
            'organization',
            'organization_name',
            'bio',
            'phone_number',
            'avatar',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'organization_name',
            'created_at',
            'updated_at',
        )


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
    organization = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=Organization.objects.all()
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'bio', 'phone_number', 'organization')

    def validate_organization(self, value: Organization):
        """Validate user has access to the selected organization."""
        user = self.instance or getattr(self.context.get('request'), 'user', None)
        if value is not None and not user_can_access_organization(user, value):
            raise serializers.ValidationError('Invalid organization or you are not a member of this organization.')
        return value

    def update(self, instance, validated_data):
        """Update user and profile data."""
        profile, _ = Profile.objects.get_or_create(user=instance)
        for attr in ('email', 'first_name', 'last_name'):
            if attr in validated_data:
                setattr(instance, attr, validated_data.pop(attr))
        for attr in ('bio', 'phone_number', 'organization'):
            if attr in validated_data:
                setattr(profile, attr, validated_data.pop(attr))
        instance.save()
        profile.save()
        return instance
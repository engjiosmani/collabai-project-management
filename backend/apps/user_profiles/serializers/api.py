from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from apps.organizations.models import Organization, OrganizationMember
from common.tenant_access import user_can_access_organization
from ..models import Profile
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
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.avatar:
            request = self.context.get('request')
            if request:
                data['avatar'] = request.build_absolute_uri(instance.avatar.url)
        else:
            data['avatar'] = None
        return data
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
        user = self.instance or getattr(self.context.get('request'), 'user', None)
        if value is not None and not user_can_access_organization(user, value):
            raise serializers.ValidationError('Invalid organization or you are not a member of this organization.')
        return value
    def update(self, instance, validated_data):
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

class ProfileDetailSerializer(serializers.ModelSerializer):
    """Used for GET /api/v1/profile/ and PATCH /api/v1/profile/"""
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')
    avatar = serializers.ImageField(required=False, allow_null=True)
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'date_joined', 'bio', 'phone_number', 'avatar',
        )
        read_only_fields = ('id', 'username', 'is_active', 'date_joined')
    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            profile = instance.profile
        except Profile.DoesNotExist:
            profile = None
        data['bio'] = getattr(profile, 'bio', '')
        data['phone_number'] = getattr(profile, 'phone_number', '')
        if profile and profile.avatar:
            request = self.context.get('request')
            data['avatar'] = (
                request.build_absolute_uri(profile.avatar.url)
                if request else profile.avatar.url
            )
        else:
            data['avatar'] = None
        return data
    def update(self, instance, validated_data):
        profile_fields = {}
        for field in ('bio', 'phone_number', 'avatar'):
            if field in validated_data:
                profile_fields[field] = validated_data.pop(field)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if profile_fields:
            profile, _ = Profile.objects.get_or_create(user=instance)
            for attr, val in profile_fields.items():
                setattr(profile, attr, val)
            profile.save()
        return instance
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
class MembershipWorkspaceSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='workspace.id')
    name = serializers.CharField(source='workspace.name')
    role = serializers.CharField()
class MembershipOrganizationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
class MembershipSerializer(serializers.Serializer):
    organization = serializers.SerializerMethodField()
    role = serializers.CharField()
    workspaces = serializers.SerializerMethodField()
    @extend_schema_field(MembershipOrganizationSerializer)
    def get_organization(self, obj) -> dict:
        return {'id': obj.organization.id, 'name': obj.organization.name}
    @extend_schema_field(MembershipWorkspaceSerializer(many=True))
    def get_workspaces(self, obj) -> list[dict]:
        from apps.workspaces.models import TeamMember
        memberships = TeamMember.objects.filter(
            workspace__organization=obj.organization,
            user=obj.user,
        ).select_related('workspace')
        return MembershipWorkspaceSerializer(memberships, many=True).data

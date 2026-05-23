import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth import authenticate


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = get_user_model()
        fields = ['id', 'email', 'password']
        read_only_fields = ['id']

    def validate_email(self, value):
        User = get_user_model()
        normalized_email = value.lower().strip()

        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError('A user with this email already exists.')

        return normalized_email

    def validate_password(self, value):
        validate_password(value)

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', value):
            raise serializers.ValidationError('Password must contain at least one number.')
        if not re.search(r'[^A-Za-z0-9]', value):
            raise serializers.ValidationError('Password must contain at least one special character.')

        return value

    def create(self, validated_data):
        from .services.register_service import RegisterService

        return RegisterService().register_user(
            email=validated_data['email'],
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password', '')

        user = authenticate(
            request=self.context.get('request'),
            username=email,  # RegisterService sets username=email
            password=password,
        )

        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been disabled.')

        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AccessTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    database = serializers.CharField()
    groq_configured = serializers.BooleanField()


class ActivityByActionSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    total_activity_logs = serializers.IntegerField()
    recent_activity = serializers.ListField(child=serializers.DictField())
    activity_by_action = ActivityByActionSerializer(many=True)


class MetricsResponseSerializer(serializers.Serializer):
    users = serializers.IntegerField()
    organizations = serializers.IntegerField()
    workspaces = serializers.IntegerField()
    roles = serializers.IntegerField()
    permissions = serializers.IntegerField()
    team_members = serializers.IntegerField()
    workspace_invites = serializers.IntegerField()
    projects = serializers.IntegerField()
    tasks = serializers.IntegerField()
    comments = serializers.IntegerField()
    activity_logs = serializers.IntegerField()
    notifications = serializers.IntegerField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(min_length=8, write_only=True, required=False)

    def validate(self, attrs):
        password = attrs.get('password') or attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if not password:
            raise serializers.ValidationError({'password': 'This field is required.'})

        if confirm_password is not None and password != confirm_password:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

        validate_password(password)
        attrs['new_password'] = password
        return attrs

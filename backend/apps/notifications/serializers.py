from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'user',
            'user_email',
            'title',
            'message',
            'is_read',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate_title(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text

    def validate_message(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        return text


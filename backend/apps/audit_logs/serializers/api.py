from rest_framework import serializers

from ..models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_email',
            'action',
            'entity_name',
            'entity_id',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

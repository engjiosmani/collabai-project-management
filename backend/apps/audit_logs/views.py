from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import AuditLog
from .serializers import AuditLogSerializer


@extend_schema_view(
    list=extend_schema(tags=['Audit logs'], summary='List audit logs'),
    retrieve=extend_schema(tags=['Audit logs'], summary='Retrieve audit log'),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['action', 'entity_name', 'user__email']
    ordering_fields = ['created_at', 'updated_at', 'action', 'entity_name']
    filterset_fields = ['action', 'entity_name', 'entity_id', 'user']

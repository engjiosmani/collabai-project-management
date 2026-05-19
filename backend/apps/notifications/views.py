from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.cache import CachedListMixin, NAMESPACE_NOTIFICATIONS, bump_version
from common.permissions import IsOwner

from .filters import NotificationFilter
from .models import Notification
from .serializers import NotificationSerializer


@extend_schema_view(
	list=extend_schema(tags=['Notifications'], summary='List notifications'),
	retrieve=extend_schema(tags=['Notifications'], summary='Retrieve notification'),
	create=extend_schema(tags=['Notifications'], summary='Create notification'),
	update=extend_schema(tags=['Notifications'], summary='Update notification'),
	partial_update=extend_schema(tags=['Notifications'], summary='Partially update notification'),
	destroy=extend_schema(tags=['Notifications'], summary='Delete notification'),
)
class NotificationViewSet(CachedListMixin, viewsets.ModelViewSet):
	cache_namespace = NAMESPACE_NOTIFICATIONS
	cache_default_list_path = '/api/v1/notifications/'

	serializer_class = NotificationSerializer
	permission_classes = [IsAuthenticated, IsOwner]
	filterset_class = NotificationFilter
	search_fields = ('title', 'message')
	ordering_fields = ('created_at', 'updated_at', 'title', 'is_read')
	ordering = ('-created_at',)

	def get_queryset(self) -> QuerySet[Notification]:
		if getattr(self, 'swagger_fake_view', False):
			return Notification.objects.none()
		user = self.request.user
		return Notification.objects.filter(user=user).select_related('user').order_by('-created_at')

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@extend_schema(tags=['Notifications'], summary='Mark notification as read')
	@action(detail=True, methods=['post'])
	def mark_read(self, request, pk=None):
		notification = self.get_object()
		if not notification.is_read:
			notification.is_read = True
			notification.save(update_fields=['is_read', 'updated_at'])
			bump_version(NAMESPACE_NOTIFICATIONS)
		return Response(self.get_serializer(notification).data, status=status.HTTP_200_OK)

	@extend_schema(tags=['Notifications'], summary='Mark all notifications as read')
	@action(detail=False, methods=['post'])
	def mark_all_read(self, request):
		updated = self.get_queryset().filter(is_read=False).update(is_read=True)
		if updated:
			bump_version(NAMESPACE_NOTIFICATIONS)
		return Response({'updated': updated}, status=status.HTTP_200_OK)

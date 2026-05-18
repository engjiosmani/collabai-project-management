from django.db.models import Count, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from rest_framework.permissions import IsAuthenticated

from .models import Organization
from .serializers import OrganizationSerializer


@extend_schema_view(
	list=extend_schema(tags=['Organizations'], summary='List organizations'),
	retrieve=extend_schema(tags=['Organizations'], summary='Retrieve organization'),
	create=extend_schema(tags=['Organizations'], summary='Create organization'),
	update=extend_schema(tags=['Organizations'], summary='Update organization'),
	partial_update=extend_schema(tags=['Organizations'], summary='Partially update organization'),
	destroy=extend_schema(tags=['Organizations'], summary='Delete organization'),
)
class OrganizationViewSet(viewsets.ModelViewSet):
	serializer_class = OrganizationSerializer
	permission_classes = [IsAuthenticated]
	search_fields = ('name', 'description')
	ordering_fields = ('created_at', 'updated_at', 'name')
	ordering = ('name',)

	def get_queryset(self) -> QuerySet[Organization]:
		return Organization.objects.annotate(workspace_count=Count('workspaces')).order_by('name')

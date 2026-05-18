from django.core.cache import cache
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.response import Response

from common.cache import make_list_key
from common.permissions import IsWorkspaceTeamMember
from common.tenant_viewset import TenantScopedViewSet

from .filters import ProjectFilter
from .models import Project
from .serializers import ProjectSerializer

CACHE_NAMESPACE = 'projects'


@extend_schema_view(
    list=extend_schema(tags=['Projects'], summary='List projects'),
    retrieve=extend_schema(tags=['Projects'], summary='Retrieve project'),
    create=extend_schema(tags=['Projects'], summary='Create project'),
    update=extend_schema(tags=['Projects'], summary='Update project'),
    partial_update=extend_schema(tags=['Projects'], summary='Partially update project'),
    destroy=extend_schema(tags=['Projects'], summary='Delete project'),
)
class ProjectViewSet(TenantScopedViewSet):
    """
    CRUD for projects scoped to workspaces the current user belongs to.
    Filter by workspace, organization, is_active, and date ranges (see query params).
    Sort with ordering=-created_at,name,...
    """
    queryset = Project.objects.select_related(
        'workspace',
        'workspace__organization'
    )

    serializer_class = ProjectSerializer
    permission_classes = [IsWorkspaceTeamMember]
    filterset_class = ProjectFilter
    search_fields = ('name', 'description')
    ordering_fields = ('created_at', 'updated_at', 'name', 'start_date', 'due_date', 'is_active')
    ordering = ('-created_at',)



    def list(self, request, *args, **kwargs):
        cache_key = make_list_key(CACHE_NAMESPACE, request.user.pk, request.get_full_path())
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data)
        return response

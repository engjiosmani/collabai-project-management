from drf_spectacular.utils import extend_schema, extend_schema_view

from common.cache import CachedListMixin, NAMESPACE_PROJECTS
from common.permissions import IsOrganizationMember
from common.tenant_viewset import TenantScopedViewSet
from common.role_permissions import IsAdmin

from .filters import ProjectFilter
from .models import Project
from .serializers import ProjectSerializer


@extend_schema_view(
    list=extend_schema(tags=['Projects'], summary='List projects'),
    retrieve=extend_schema(tags=['Projects'], summary='Retrieve project'),
    create=extend_schema(tags=['Projects'], summary='Create project'),
    update=extend_schema(tags=['Projects'], summary='Update project'),
    partial_update=extend_schema(tags=['Projects'], summary='Partially update project'),
    destroy=extend_schema(tags=['Projects'], summary='Delete project'),
)
class ProjectViewSet(CachedListMixin, TenantScopedViewSet):
    cache_namespace = NAMESPACE_PROJECTS
    cache_default_list_path = '/api/v1/projects/'
    """
    CRUD for projects scoped to organizations the current user belongs to.
    """
    queryset = Project.objects.select_related('organization')

    serializer_class = ProjectSerializer
    permission_classes = [IsOrganizationMember]
    filterset_class = ProjectFilter
    search_fields = ('name', 'description', 'organization__name')
    ordering_fields = (
        'created_at',
        'updated_at',
        'name',
        'start_date',
        'due_date',
        'is_active',
        'organization__name',
    )
    ordering = ('-created_at',)

    def get_permissions(self):

        if self.action == "destroy":
            return [IsAdmin()]

        return super().get_permissions()

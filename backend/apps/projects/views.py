from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from common.permissions import IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

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
class ProjectViewSet(viewsets.ModelViewSet):
    """
    CRUD for projects scoped to workspaces the current user belongs to.
    Filter by workspace, organization, is_active, and date ranges (see query params).
    Sort with ordering=-created_at,name,...
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsWorkspaceTeamMember]
    filterset_class = ProjectFilter
    search_fields = ('name', 'description')
    ordering_fields = ('created_at', 'updated_at', 'name', 'start_date', 'due_date', 'is_active')
    ordering = ('-created_at',)

    def get_queryset(self) -> QuerySet[Project]:
        ws_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return Project.objects.filter(workspace_id__in=ws_ids).select_related('workspace', 'workspace__organization')
from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.cache import CachedListMixin, NAMESPACE_PROJECTS
from common.permissions import IsOrganizationMember
from common.role_permissions import IsAdmin, IsManagerOrAdmin
from common.tenant_viewset import TenantScopedViewSet

from .filters import ProjectFilter
from .models import Project, ProjectMember
from .serializers import AddProjectMemberSerializer, ProjectMemberSerializer, ProjectSerializer

User = get_user_model()


@extend_schema_view(
    list=extend_schema(tags=['Projects'], summary='List projects'),
    retrieve=extend_schema(tags=['Projects'], summary='Retrieve project'),
    create=extend_schema(tags=['Projects'], summary='Create project'),
    update=extend_schema(tags=['Projects'], summary='Update project (manager/admin only)'),
    partial_update=extend_schema(tags=['Projects'], summary='Partially update project (manager/admin only)'),
    destroy=extend_schema(tags=['Projects'], summary='Delete project (admin only)'),
)
class ProjectViewSet(CachedListMixin, TenantScopedViewSet):
    cache_namespace = NAMESPACE_PROJECTS
    cache_default_list_path = '/api/v1/projects/'

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
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action in ('update', 'partial_update'):
            return [IsManagerOrAdmin()]
        return super().get_permissions()

    # ── Project Members ──────────────────────────────────────────────────────

    @extend_schema(
        tags=['Projects'],
        summary='List project members',
        responses={200: ProjectMemberSerializer(many=True)},
    )
    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == 'GET':
            members = ProjectMember.objects.filter(project=project).select_related('user')
            return Response(
                ProjectMemberSerializer(members, many=True).data,
                status=status.HTTP_200_OK,
            )

        # POST — add member
        serializer = AddProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        user = User.objects.get(pk=user_id)

        member, created = ProjectMember.objects.get_or_create(project=project, user=user)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ProjectMemberSerializer(member).data,
            status=status_code,
        )

    @extend_schema(
        tags=['Projects'],
        summary='Remove a project member',
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            )
        ],
        responses={204: None},
    )
    @action(
        detail=True,
        methods=['delete'],
        url_path=r'members/(?P<user_id>[^/.]+)',
    )
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        deleted, _ = ProjectMember.objects.filter(
            project=project, user_id=user_id
        ).delete()
        if not deleted:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
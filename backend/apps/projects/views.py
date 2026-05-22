from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.organizations.models import OrganizationMember
from common.cache import CachedListMixin, NAMESPACE_PROJECTS
from common.permissions import IsOrganizationMember
from common.tenant_viewset import TenantScopedViewSet
from common.role_permissions import (
    IsOrgAdmin,
    project_visibility_q,
    user_is_manager_or_above,
)
from apps.audit_logs.services import write_audit_log

from .filters import ProjectFilter
from .models import Project, ProjectMember
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
            return [IsOrgAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()

        org_ids = getattr(self.request, 'organization_ids', [])
        return (
            self.queryset.filter(
                project_visibility_q(self.request.user, org_ids),
                is_active=True,
            )
            .distinct()
        )

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        if not user_is_manager_or_above(self.request.user, organization):
            raise PermissionDenied('You must be a manager or above to create projects.')
        project = serializer.save()
        ProjectMember.objects.get_or_create(project=project, user=self.request.user)

    def perform_update(self, serializer):
        organization = serializer.validated_data.get(
            'organization',
            serializer.instance.organization,
        )
        if not user_is_manager_or_above(self.request.user, organization):
            raise PermissionDenied('You must be a manager or above to update projects.')
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        write_audit_log(
            self.request.user,
            'PROJECT_SOFT_DELETED',
            'Project',
            instance.pk,
            {'organization_id': instance.organization_id, 'name': instance.name},
        )

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == 'GET':
            memberships = project.members.select_related('user').order_by('user__email')
            return Response(
                [
                    {
                        'id': membership.pk,
                        'user_id': membership.user_id,
                        'email': membership.user.email,
                        'username': membership.user.username,
                        'created_at': membership.created_at,
                    }
                    for membership in memberships
                ],
                status=status.HTTP_200_OK,
            )

        if not user_is_manager_or_above(request.user, project.organization):
            raise PermissionDenied('You must be a manager or above to add project members.')

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'user_id': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not OrganizationMember.objects.filter(
            organization=project.organization,
            user_id=user_id,
        ).exists():
            return Response(
                {'detail': 'User must be an organization member before joining a project.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership, created = ProjectMember.objects.get_or_create(
            project=project,
            user_id=user_id,
        )
        if not created:
            return Response(
                {'detail': 'User is already a project member.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        write_audit_log(
            request.user,
            'PROJECT_MEMBER_ADDED',
            'ProjectMember',
            membership.pk,
            {
                'organization_id': project.organization_id,
                'project_id': project.pk,
                'target_user_id': membership.user_id,
            },
        )
        return Response(
            {'id': membership.pk, 'user_id': membership.user_id},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'members/(?P<user_id>[^/.]+)',
    )
    def member_detail(self, request, pk=None, user_id=None):
        project = self.get_object()
        if not user_is_manager_or_above(request.user, project.organization):
            raise PermissionDenied('You must be a manager or above to remove project members.')

        membership = ProjectMember.objects.filter(project=project, user_id=user_id).first()
        if membership is None:
            return Response({'detail': 'Project member not found.'}, status=status.HTTP_404_NOT_FOUND)

        membership_id = membership.pk
        membership.delete()
        write_audit_log(
            request.user,
            'PROJECT_MEMBER_REMOVED',
            'ProjectMember',
            membership_id,
            {
                'organization_id': project.organization_id,
                'project_id': project.pk,
                'target_user_id': int(user_id),
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

from django.db.models import Count, QuerySet
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from common.cache import CachedListMixin, NAMESPACE_WORKSPACES
from common.permissions import IsAuthenticatedReadOnly, IsWorkspaceTeamMember
from common.role_permissions import (
    can_workspace_admin_assign_role,
    user_is_org_admin,
    user_is_workspace_admin_or_org_admin,
)
from common.tenant_access import organization_ids_for_request, organizations_queryset_for_user
from apps.audit_logs.services import write_audit_log

from .filters import WorkspaceFilter
from .models import JobRole, TeamMember, Workspace
from .serializers import (
    JobRoleSerializer,
    TeamMemberJobRoleUpdateSerializer,
    TeamMemberSerializer,
    WorkspaceSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Workspaces'], summary='List workspaces'),
    retrieve=extend_schema(tags=['Workspaces'], summary='Retrieve workspace'),
    create=extend_schema(tags=['Workspaces'], summary='Create workspace'),
    update=extend_schema(tags=['Workspaces'], summary='Update workspace'),
    partial_update=extend_schema(tags=['Workspaces'], summary='Partially update workspace'),
    destroy=extend_schema(tags=['Workspaces'], summary='Delete workspace'),
    set_member_job_role=extend_schema(
        tags=['Workspaces'],
        summary='Set a member job role',
        request=TeamMemberJobRoleUpdateSerializer,
        parameters=[
            OpenApiParameter(
                name='member_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace team member ID.',
            ),
        ],
        responses={200: TeamMemberSerializer},
    ),
)
class WorkspaceViewSet(CachedListMixin, viewsets.ModelViewSet):
    cache_namespace = NAMESPACE_WORKSPACES
    cache_default_list_path = '/api/v1/workspaces/'

    serializer_class = WorkspaceSerializer
    permission_classes = [IsWorkspaceTeamMember]
    filterset_class = WorkspaceFilter
    search_fields = ('name', 'organization__name')
    ordering_fields = ('created_at', 'updated_at', 'name', 'is_active')
    ordering = ('name',)

    def get_queryset(self) -> QuerySet[Workspace]:
        """
        Get workspaces that belong to organizations the user is a member of.

        For superusers: all workspaces
        For regular users: workspaces in user's organizations
        """
        if getattr(self, 'swagger_fake_view', False):
            return Workspace.objects.none()

        # Get organization IDs the user belongs to
        org_ids = organization_ids_for_request(self.request)

        return (
            Workspace.objects.filter(organization_id__in=org_ids, is_active=True)
            .select_related('organization')
            .annotate(
                member_count=Count('team_members', distinct=True),
            )
            .order_by('name')
        )

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        if not user_is_org_admin(self.request.user, organization):
            raise PermissionDenied('Only organization admins can create workspaces.')
        serializer.save()

    def perform_update(self, serializer):
        workspace = serializer.instance
        organization = serializer.validated_data.get(
            'organization',
            workspace.organization,
        )
        if not user_is_workspace_admin_or_org_admin(
            self.request.user,
            organization,
            workspace,
        ):
            raise PermissionDenied('Only org admins or workspace admins can update workspaces.')
        serializer.save()

    def perform_destroy(self, instance):
        if not user_is_org_admin(self.request.user, instance.organization):
            raise PermissionDenied('Only organization admins can delete workspaces.')
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        write_audit_log(
            self.request.user,
            'WORKSPACE_SOFT_DELETED',
            'Workspace',
            instance.pk,
            {'organization_id': instance.organization_id, 'name': instance.name},
        )

    @action(detail=True, methods=['get'])
    @extend_schema(tags=['Workspaces'], summary='List workspace members')
    def members(self, request, pk=None):
        workspace = self.get_object()

        members = TeamMember.objects.filter(
            workspace=workspace
        ).select_related(
            'user',
            'job_role',
            'workspace',
        )

        return Response(
            TeamMemberSerializer(members, many=True).data,
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'members/(?P<member_id>[^/.]+)/job-role',
    )
    @extend_schema(
        tags=['Workspaces'],
        summary='Set a member job role',
        request=TeamMemberJobRoleUpdateSerializer,
        parameters=[
            OpenApiParameter(
                name='member_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace team member ID.',
            ),
        ],
        responses={200: TeamMemberSerializer},
    )
    def set_member_job_role(self, request, pk=None, member_id=None):
        workspace = self.get_object()

        if not user_is_workspace_admin_or_org_admin(
            request.user,
            workspace.organization,
            workspace,
        ):
            raise PermissionDenied('Only org admins or workspace admins can update workspace members.')

        member = TeamMember.objects.filter(
            pk=member_id,
            workspace=workspace
        ).first()

        if member is None:
            return Response(
                {'detail': 'Member not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TeamMemberJobRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_role_id = serializer.validated_data.get('job_role_id')

        if job_role_id is None:
            member.job_role = None
        else:
            member.job_role = JobRole.objects.get(pk=job_role_id)

        member.save(update_fields=['job_role', 'updated_at'])

        member = TeamMember.objects.select_related(
            'user',
            'job_role',
            'workspace',
        ).get(pk=member.pk)

        return Response(TeamMemberSerializer(member).data)


@extend_schema_view(
    list=extend_schema(tags=['Job roles'], summary='List job roles'),
    retrieve=extend_schema(tags=['Job roles'], summary='Retrieve job role'),
)
class JobRoleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JobRoleSerializer
    permission_classes = [IsAuthenticatedReadOnly]
    queryset = JobRole.objects.filter(is_active=True).order_by('name')
    search_fields = ('name', 'code', 'description')
    ordering_fields = ('name', 'code')
    ordering = ('name',)

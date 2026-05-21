import uuid
from datetime import timedelta
from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.cache import CachedListMixin, NAMESPACE_ORGANIZATIONS
from common.permissions import IsOrganizationMember
from common.tenant_access import organizations_queryset_for_user
from apps.workspaces.models import JobRole, TeamMember, Workspace
from .models import Organization, OrganizationInvite, OrganizationMember
from .serializers import (
    AddWorkspaceMemberSerializer,
    OrgMemberRoleUpdateSerializer,
    OrganizationInviteCreateSerializer,
    OrganizationInviteSerializer,
    OrganizationMemberJobRoleUpdateSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
    TeamMemberInOrgSerializer,
    WorkspaceInOrgSerializer,
    WorkspaceMemberRoleUpdateSerializer,
)
# ── Permission helpers ────────────────────────────────────────────────────────
def _is_org_admin(user, organization_id):
    if getattr(user, 'is_superuser', False):
        return True
    return OrganizationMember.objects.filter(
        organization_id=organization_id,
        user=user,
        role=OrganizationMember.ORG_ADMIN,
    ).exists()
def _is_workspace_admin_or_org_admin(user, workspace_id, organization_id):
    if getattr(user, 'is_superuser', False):
        return True
    if _is_org_admin(user, organization_id):
        return True
    return TeamMember.objects.filter(
        workspace_id=workspace_id,
        user=user,
        role=TeamMember.WORKSPACE_ADMIN,
    ).exists()
# ── Organization ViewSet ──────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(tags=['Organizations'], summary='List my organizations'),
    retrieve=extend_schema(tags=['Organizations'], summary='Retrieve organization'),
    create=extend_schema(tags=['Organizations'], summary='Create organization (creator becomes org_admin)'),
    update=extend_schema(tags=['Organizations'], summary='Update organization (org_admin only)'),
    partial_update=extend_schema(tags=['Organizations'], summary='Partially update organization (org_admin only)'),
    destroy=extend_schema(tags=['Organizations'], summary='Delete organization (org_admin only)'),
)
class OrganizationViewSet(CachedListMixin, viewsets.ModelViewSet):
    cache_namespace = NAMESPACE_ORGANIZATIONS
    cache_default_list_path = '/api/v1/organizations/'
    serializer_class = OrganizationSerializer
    permission_classes = [IsOrganizationMember]
    search_fields = ('name', 'description')
    ordering_fields = ('created_at', 'updated_at', 'name')
    ordering = ('name',)
    def get_queryset(self) -> QuerySet[Organization]:
        if getattr(self, 'swagger_fake_view', False):
            return Organization.objects.none()
        org_ids = organizations_queryset_for_user(self.request.user).values_list('pk', flat=True)
        return (
            Organization.objects.filter(pk__in=org_ids)
            .annotate(
                project_count=Count('projects', distinct=True),
                member_count=Count('members', distinct=True),
            )
            .order_by('name')
        )
    def perform_create(self, serializer):
        organization = serializer.save()
        OrganizationMember.objects.get_or_create(
            organization=organization,
            user=self.request.user,
            defaults={'role': OrganizationMember.ORG_ADMIN},
        )
    def perform_update(self, serializer):
        if not _is_org_admin(self.request.user, serializer.instance.pk):
            raise PermissionDenied('Only organization admins can update this organization.')
        serializer.save()
    def perform_destroy(self, instance):
        if not _is_org_admin(self.request.user, instance.pk):
            raise PermissionDenied('Only organization admins can delete this organization.')
        instance.delete()
    # ── Members ───────────────────────────────────────────────────────────────
    @extend_schema(tags=['Organizations'], summary='List organization members')
    @action(detail=True, methods=['get'], url_path='members', url_name='members')
    def members(self, request, pk=None):
        organization = self.get_object()
        qs = OrganizationMember.objects.filter(organization=organization).select_related(
            'user', 'job_role', 'organization'
        )
        return Response(OrganizationMemberSerializer(qs, many=True).data)
    @extend_schema(
        methods=['patch'],
        tags=['Organizations'],
        summary='Update member role or job_role (org_admin only)',
        request=OrgMemberRoleUpdateSerializer,
        responses={200: OrganizationMemberSerializer},
        parameters=[OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @extend_schema(
        methods=['delete'],
        tags=['Organizations'],
        summary='Remove member from organization (org_admin only)',
        responses={204: None},
        parameters=[OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'members/(?P<user_id>[^/.]+)',
        url_name='member-detail',
    )
    def member_detail(self, request, pk=None, user_id=None):
        organization = self.get_object()
        if not _is_org_admin(request.user, organization.pk):
            return Response(
                {'detail': 'Only organization admins can modify members.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        member = (
            OrganizationMember.objects.filter(organization=organization, user_id=user_id)
            .select_related('user', 'job_role')
            .first()
        )
        if member is None:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'PATCH':
            serializer = OrgMemberRoleUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            if 'role' in data:
                member.role = data['role']
            if 'job_role_id' in data:
                job_role_id = data['job_role_id']
                if job_role_id is None:
                    member.job_role = None
                else:
                    job_role = JobRole.objects.filter(pk=job_role_id).first()
                    if job_role is None:
                        return Response({'detail': 'Job role not found.'}, status=status.HTTP_404_NOT_FOUND)
                    member.job_role = job_role
            member.save()
            member.refresh_from_db()
            return Response(OrganizationMemberSerializer(member).data, status=status.HTTP_200_OK)
        # DELETE
        if member.user_id == request.user.pk:
            return Response(
                {'detail': 'You cannot remove yourself from the organization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Also remove from every workspace inside this org
        TeamMember.objects.filter(
            workspace__organization=organization,
            user_id=user_id,
        ).delete()
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    # ── Job-role shortcut (kept for backward compat) ──────────────────────────
    @extend_schema(
        tags=['Organizations'],
        summary='Set a member job role (org_admin only)',
        request=OrganizationMemberJobRoleUpdateSerializer,
        responses={200: OrganizationMemberSerializer},
        parameters=[OpenApiParameter('member_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(
        detail=True,
        methods=['patch'],
        url_path=r'members/(?P<member_id>[^/.]+)/job-role',
        url_name='member-job-role',
    )
    def set_member_job_role(self, request, pk=None, member_id=None):
        organization = self.get_object()
        member = OrganizationMember.objects.filter(pk=member_id, organization=organization).first()
        if member is None:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrganizationMemberJobRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_role_id = serializer.validated_data.get('job_role_id')
        if job_role_id is None:
            member.job_role = None
        else:
            job_role = JobRole.objects.filter(pk=job_role_id).first()
            if job_role is None:
                return Response({'detail': 'Job role not found.'}, status=status.HTTP_404_NOT_FOUND)
            member.job_role = job_role
        member.save(update_fields=['job_role', 'updated_at'])
        member = OrganizationMember.objects.select_related('user', 'job_role', 'organization').get(pk=member.pk)
        return Response(OrganizationMemberSerializer(member).data)
    # ── Invitations ───────────────────────────────────────────────────────────
    @extend_schema(
        tags=['Organizations'],
        summary='Invite a user by email (org_admin only)',
        request=OrganizationInviteCreateSerializer,
        responses={201: OrganizationInviteSerializer},
    )
    @action(detail=True, methods=['post'], url_path='invite', url_name='invite')
    def invite(self, request, pk=None):
        organization = self.get_object()
        if not _is_org_admin(request.user, organization.pk):
            return Response(
                {'detail': 'Only organization admins can send invitations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OrganizationInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data['email']
        role = data.get('role', OrganizationInvite.MEMBER)
        workspace_id = data.get('workspace_id')
        workspace = None
        if workspace_id:
            workspace = Workspace.objects.filter(pk=workspace_id, organization=organization).first()
            if workspace is None:
                return Response(
                    {'detail': 'Workspace not found in this organization.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        invite, created = OrganizationInvite.objects.update_or_create(
            organization=organization,
            email=email,
            defaults={
                'role': role,
                'workspace': workspace,
                'token': str(uuid.uuid4()),
                'is_accepted': False,
                'expires_at': timezone.now() + timedelta(days=7),
            },
        )
        # ASYNC-02 will wire in: send_invite_email.delay(invite.id)
        return Response(
            OrganizationInviteSerializer(invite).data,
            status=status.HTTP_201_CREATED,
        )
    # ── Workspaces ────────────────────────────────────────────────────────────
    @extend_schema(
        methods=['get'],
        tags=['Organizations'],
        summary='List workspaces in this organization',
        responses={200: WorkspaceInOrgSerializer(many=True)},
    )
    @extend_schema(
        methods=['post'],
        tags=['Organizations'],
        summary='Create a workspace in this organization (org_admin only)',
        request=WorkspaceInOrgSerializer,
        responses={201: WorkspaceInOrgSerializer},
    )
    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='workspaces',
        url_name='workspaces',
    )
    def org_workspaces(self, request, pk=None):
        organization = self.get_object()
        if request.method == 'GET':
            workspaces = (
                Workspace.objects.filter(organization=organization)
                .annotate(
                    member_count=Count('team_members', distinct=True),
                )
                .order_by('name')
            )
            return Response(WorkspaceInOrgSerializer(workspaces, many=True).data)
        # POST
        if not _is_org_admin(request.user, organization.pk):
            return Response(
                {'detail': 'Only organization admins can create workspaces.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = WorkspaceInOrgSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = serializer.save(organization=organization)
        return Response(WorkspaceInOrgSerializer(workspace).data, status=status.HTTP_201_CREATED)
    @extend_schema(
        methods=['get'],
        tags=['Organizations'],
        summary='Retrieve workspace detail',
        responses={200: WorkspaceInOrgSerializer},
        parameters=[OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @extend_schema(
        methods=['put', 'patch'],
        tags=['Organizations'],
        summary='Update workspace (org_admin or workspace_admin)',
        request=WorkspaceInOrgSerializer,
        responses={200: WorkspaceInOrgSerializer},
        parameters=[OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @extend_schema(
        methods=['delete'],
        tags=['Organizations'],
        summary='Delete workspace (org_admin only)',
        responses={204: None},
        parameters=[OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(
        detail=True,
        methods=['get', 'put', 'patch', 'delete'],
        url_path=r'workspaces/(?P<ws_id>[^/.]+)',
        url_name='workspace-detail',
    )
    def org_workspace_detail(self, request, pk=None, ws_id=None):
        organization = self.get_object()
        workspace = get_object_or_404(Workspace, pk=ws_id, organization=organization)
        if request.method == 'GET':
            workspace = (
                Workspace.objects.filter(pk=ws_id, organization=organization)
                .annotate(
                    member_count=Count('team_members', distinct=True),
                )
                .first()
            )
            return Response(WorkspaceInOrgSerializer(workspace).data)
        if not _is_workspace_admin_or_org_admin(request.user, workspace.pk, organization.pk):
            return Response(
                {'detail': 'Only org admins or workspace admins can modify this workspace.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method in ('PUT', 'PATCH'):
            partial = request.method == 'PATCH'
            serializer = WorkspaceInOrgSerializer(workspace, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            workspace = (
                Workspace.objects.filter(pk=workspace.pk)
                .annotate(
                    member_count=Count('team_members', distinct=True),
                )
                .first()
            )
            return Response(WorkspaceInOrgSerializer(workspace).data)
        # DELETE — org_admin only
        if not _is_org_admin(request.user, organization.pk):
            return Response(
                {'detail': 'Only organization admins can delete workspaces.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    # ── Workspace members ─────────────────────────────────────────────────────
    @extend_schema(
        methods=['get'],
        tags=['Organizations'],
        summary='List workspace members',
        responses={200: TeamMemberInOrgSerializer(many=True)},
        parameters=[OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @extend_schema(
        methods=['post'],
        tags=['Organizations'],
        summary='Add an org member to workspace (org_admin or workspace_admin)',
        request=AddWorkspaceMemberSerializer,
        responses={201: TeamMemberInOrgSerializer},
        parameters=[OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(
        detail=True,
        methods=['get', 'post'],
        url_path=r'workspaces/(?P<ws_id>[^/.]+)/members',
        url_name='workspace-members',
    )
    def workspace_members(self, request, pk=None, ws_id=None):
        organization = self.get_object()
        workspace = get_object_or_404(Workspace, pk=ws_id, organization=organization)
        if request.method == 'GET':
            qs = TeamMember.objects.filter(workspace=workspace).select_related('user', 'job_role')
            return Response(TeamMemberInOrgSerializer(qs, many=True).data)
        # POST
        if not _is_workspace_admin_or_org_admin(request.user, workspace.pk, organization.pk):
            return Response(
                {'detail': 'Only org admins or workspace admins can add workspace members.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AddWorkspaceMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        role = serializer.validated_data.get('role', TeamMember.MEMBER)
        if not OrganizationMember.objects.filter(organization=organization, user_id=user_id).exists():
            return Response(
                {'detail': 'User must be an organization member before being added to a workspace.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member, created = TeamMember.objects.get_or_create(
            workspace=workspace,
            user_id=user_id,
            defaults={'role': role},
        )
        if not created:
            return Response(
                {'detail': 'User is already a member of this workspace.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member = TeamMember.objects.select_related('user', 'job_role').get(pk=member.pk)
        return Response(TeamMemberInOrgSerializer(member).data, status=status.HTTP_201_CREATED)
    @extend_schema(
        methods=['patch'],
        tags=['Organizations'],
        summary='Change workspace member role (org_admin or workspace_admin)',
        request=WorkspaceMemberRoleUpdateSerializer,
        responses={200: TeamMemberInOrgSerializer},
        parameters=[
            OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
    )
    @extend_schema(
        methods=['delete'],
        tags=['Organizations'],
        summary='Remove member from workspace (org_admin or workspace_admin)',
        responses={204: None},
        parameters=[
            OpenApiParameter('ws_id', OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
    )
    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'workspaces/(?P<ws_id>[^/.]+)/members/(?P<user_id>[^/.]+)',
        url_name='workspace-member-detail',
    )
    def workspace_member_detail(self, request, pk=None, ws_id=None, user_id=None):
        organization = self.get_object()
        workspace = get_object_or_404(Workspace, pk=ws_id, organization=organization)
        if not _is_workspace_admin_or_org_admin(request.user, workspace.pk, organization.pk):
            return Response(
                {'detail': 'Only org admins or workspace admins can modify workspace members.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        member = (
            TeamMember.objects.filter(workspace=workspace, user_id=user_id)
            .select_related('user', 'job_role')
            .first()
        )
        if member is None:
            return Response({'detail': 'Workspace member not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'PATCH':
            serializer = WorkspaceMemberRoleUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            member.role = serializer.validated_data['role']
            member.save()
            member.refresh_from_db()
            return Response(TeamMemberInOrgSerializer(member).data)
        # DELETE
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
# ── OrganizationListForAuthenticatedView (kept for existing tests) ─────────────
class OrganizationListForAuthenticatedView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
# ── Accept Invite ─────────────────────────────────────────────────────────────
class AcceptInviteView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Organizations'],
        summary='Accept an organization invitation by token',
        responses={
            200: OrganizationMemberSerializer,
            400: None,
            404: None,
        },
    )
    def post(self, request, token):
        invite = (
            OrganizationInvite.objects.filter(token=token)
            .select_related('organization', 'workspace')
            .first()
        )
        if invite is None:
            return Response({'detail': 'Invitation not found.'}, status=status.HTTP_404_NOT_FOUND)
        if invite.is_accepted:
            return Response(
                {'detail': 'This invitation has already been accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if invite.expires_at < timezone.now():
            return Response(
                {'detail': 'This invitation has expired. Please ask an admin to send a new one.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Determine org-level role
        org_role = (
            OrganizationMember.ORG_ADMIN
            if invite.role == OrganizationInvite.ORG_ADMIN
            else OrganizationMember.MEMBER
        )
        member, _ = OrganizationMember.objects.get_or_create(
            organization=invite.organization,
            user=request.user,
            defaults={'role': org_role},
        )
        # If invite targeted a specific workspace, also add there
        if invite.workspace:
            ws_role_map = {
                OrganizationInvite.WORKSPACE_ADMIN: TeamMember.WORKSPACE_ADMIN,
                OrganizationInvite.MANAGER: TeamMember.MANAGER,
                OrganizationInvite.MEMBER: TeamMember.MEMBER,
                OrganizationInvite.ORG_ADMIN: TeamMember.MEMBER,
            }
            TeamMember.objects.get_or_create(
                workspace=invite.workspace,
                user=request.user,
                defaults={'role': ws_role_map.get(invite.role, TeamMember.MEMBER)},
            )
        invite.is_accepted = True
        invite.save(update_fields=['is_accepted', 'updated_at'])
        member = OrganizationMember.objects.select_related('user', 'job_role', 'organization').get(pk=member.pk)
        return Response(OrganizationMemberSerializer(member).data, status=status.HTTP_200_OK)

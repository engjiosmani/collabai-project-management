from django.db.models import Count, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.cache import CachedListMixin, NAMESPACE_WORKSPACES
from common.permissions import IsAuthenticatedReadOnly, IsWorkspaceInviteAccess, IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

from .filters import PermissionFilter, RoleFilter, WorkspaceFilter, WorkspaceInviteFilter
from .models import JobRole, Permission, Role, TeamMember, Workspace, WorkspaceInvite
from .serializers import (
	JobRoleSerializer,
	PermissionSerializer,
	RoleSerializer,
	TeamMemberJobRoleUpdateSerializer,
	TeamMemberSerializer,
	WorkspaceInviteSerializer,
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
		summary='Set a member job role (Backend, Frontend, DevOps, …)',
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
		if getattr(self, 'swagger_fake_view', False):
			return Workspace.objects.none()
		workspace_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
		return (
			Workspace.objects.filter(pk__in=workspace_ids)
			.select_related('organization')
			.annotate(
				member_count=Count('team_members', distinct=True),
				role_count=Count('roles', distinct=True),
				invite_count=Count('invites', distinct=True),
				project_count=Count('projects', distinct=True),
			)
			.order_by('name')
		)

	@action(detail=True, methods=['get'])
	@extend_schema(tags=['Workspaces'], summary='List workspace members')
	def members(self, request, pk=None):
		workspace = self.get_object()
		members = TeamMember.objects.filter(workspace=workspace).select_related(
			'user', 'role', 'job_role', 'workspace'
		)
		return Response(TeamMemberSerializer(members, many=True).data, status=status.HTTP_200_OK)

	@action(
		detail=True,
		methods=['patch'],
		url_path=r'members/(?P<member_id>[^/.]+)/job-role',
	)
	@extend_schema(
		tags=['Workspaces'],
		summary='Set a member job role (Backend, Frontend, DevOps, …)',
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
		member = TeamMember.objects.filter(pk=member_id, workspace=workspace).first()
		if member is None:
			return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

		serializer = TeamMemberJobRoleUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		job_role_id = serializer.validated_data.get('job_role_id')

		if job_role_id is None:
			member.job_role = None
		else:
			member.job_role = JobRole.objects.get(pk=job_role_id)
		member.save(update_fields=['job_role', 'updated_at'])

		member = TeamMember.objects.select_related('user', 'role', 'job_role', 'workspace').get(
			pk=member.pk
		)
		return Response(TeamMemberSerializer(member).data)


@extend_schema_view(
	list=extend_schema(tags=['Job roles'], summary='List job roles for task assignment'),
	retrieve=extend_schema(tags=['Job roles'], summary='Retrieve job role'),
)
class JobRoleViewSet(viewsets.ReadOnlyModelViewSet):
	serializer_class = JobRoleSerializer
	permission_classes = [IsAuthenticatedReadOnly]
	queryset = JobRole.objects.filter(is_active=True).order_by('name')
	search_fields = ('name', 'code', 'description')
	ordering_fields = ('name', 'code')
	ordering = ('name',)


@extend_schema_view(
	list=extend_schema(tags=['Roles'], summary='List roles'),
	retrieve=extend_schema(tags=['Roles'], summary='Retrieve role'),
	create=extend_schema(tags=['Roles'], summary='Create role'),
	update=extend_schema(tags=['Roles'], summary='Update role'),
	partial_update=extend_schema(tags=['Roles'], summary='Partially update role'),
	destroy=extend_schema(tags=['Roles'], summary='Delete role'),
)
class RoleViewSet(viewsets.ModelViewSet):
	serializer_class = RoleSerializer
	permission_classes = [IsWorkspaceTeamMember]
	filterset_class = RoleFilter
	search_fields = ('name', 'workspace__name')
	ordering_fields = ('created_at', 'updated_at', 'name')
	ordering = ('name',)

	def get_queryset(self) -> QuerySet[Role]:
		if getattr(self, 'swagger_fake_view', False):
			return Role.objects.none()
		workspace_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
		return Role.objects.filter(workspace_id__in=workspace_ids).select_related('workspace').prefetch_related('permissions')


@extend_schema_view(
	list=extend_schema(tags=['Permissions'], summary='List permissions'),
	retrieve=extend_schema(tags=['Permissions'], summary='Retrieve permission'),
	create=extend_schema(tags=['Permissions'], summary='Create permission'),
	update=extend_schema(tags=['Permissions'], summary='Update permission'),
	partial_update=extend_schema(tags=['Permissions'], summary='Partially update permission'),
	destroy=extend_schema(tags=['Permissions'], summary='Delete permission'),
)
class PermissionViewSet(viewsets.ModelViewSet):
	serializer_class = PermissionSerializer
	permission_classes = [IsAuthenticatedReadOnly]
	filterset_class = PermissionFilter
	search_fields = ('code', 'name', 'description')
	ordering_fields = ('created_at', 'updated_at', 'code', 'name')
	ordering = ('code',)

	def get_queryset(self) -> QuerySet[Permission]:
		return Permission.objects.all().order_by('code')


@extend_schema_view(
	list=extend_schema(tags=['Invites'], summary='List workspace invites'),
	retrieve=extend_schema(tags=['Invites'], summary='Retrieve workspace invite'),
	create=extend_schema(tags=['Invites'], summary='Create workspace invite'),
	update=extend_schema(tags=['Invites'], summary='Update workspace invite'),
	partial_update=extend_schema(tags=['Invites'], summary='Partially update workspace invite'),
	destroy=extend_schema(tags=['Invites'], summary='Delete workspace invite'),
)
class WorkspaceInviteViewSet(viewsets.ModelViewSet):
	serializer_class = WorkspaceInviteSerializer
	permission_classes = [IsWorkspaceInviteAccess]
	filterset_class = WorkspaceInviteFilter
	search_fields = ('email', 'token', 'workspace__name')
	ordering_fields = ('created_at', 'updated_at', 'email', 'is_accepted')
	ordering = ('-created_at',)

	def get_queryset(self) -> QuerySet[WorkspaceInvite]:
		if getattr(self, 'swagger_fake_view', False):
			return WorkspaceInvite.objects.none()
		workspace_ids = workspaces_queryset_for_user(self.request.user).values_list('pk', flat=True)
		email = (getattr(self.request.user, 'email', '') or '').strip().lower()
		query = Q(workspace_id__in=workspace_ids)
		if email:
			query = query | Q(email=email)
		return WorkspaceInvite.objects.filter(query).distinct().select_related('workspace', 'role')

	@extend_schema(tags=['Invites'], summary='Accept a workspace invite')
	@action(detail=True, methods=['post'])
	def accept(self, request, pk=None):
		invite = self.get_object()
		if invite.is_accepted:
			return Response({'detail': 'Invite has already been accepted.'}, status=status.HTTP_400_BAD_REQUEST)

		email = getattr(request.user, 'email', '').lower().strip()
		if invite.email != email and not request.user.is_superuser:
			return Response({'detail': 'This invite is not for the current user.'}, status=status.HTTP_403_FORBIDDEN)

		member, _ = TeamMember.objects.update_or_create(
			workspace=invite.workspace,
			user=request.user,
			defaults={'role': invite.role},
		)
		invite.is_accepted = True
		invite.save(update_fields=['is_accepted', 'updated_at'])
		return Response(
			{
				'invite': WorkspaceInviteSerializer(invite, context={'request': request}).data,
				'member': TeamMemberSerializer(member, context={'request': request}).data,
			},
			status=status.HTTP_200_OK,
		)

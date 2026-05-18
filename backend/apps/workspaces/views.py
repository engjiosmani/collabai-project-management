from django.db.models import Count, Q, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAuthenticatedReadOnly, IsWorkspaceInviteAccess, IsWorkspaceTeamMember
from common.workspace_access import workspaces_queryset_for_user

from .filters import PermissionFilter, RoleFilter, WorkspaceFilter, WorkspaceInviteFilter
from .models import Permission, Role, TeamMember, Workspace, WorkspaceInvite
from .serializers import (
	PermissionSerializer,
	RoleSerializer,
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
)
class WorkspaceViewSet(viewsets.ModelViewSet):
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
		members = TeamMember.objects.filter(workspace=workspace).select_related('user', 'role', 'workspace')
		return Response(TeamMemberSerializer(members, many=True).data, status=status.HTTP_200_OK)


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

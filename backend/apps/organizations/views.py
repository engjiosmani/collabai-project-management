from django.db.models import Count, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.cache import CachedListMixin, NAMESPACE_ORGANIZATIONS
from common.permissions import IsOrganizationMember
from common.tenant_access import organizations_queryset_for_user

from apps.workspaces.models import JobRole

from .models import Organization, OrganizationMember
from .serializers import (
    OrganizationMemberJobRoleUpdateSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Organizations'], summary='List organizations'),
    retrieve=extend_schema(tags=['Organizations'], summary='Retrieve organization'),
    create=extend_schema(tags=['Organizations'], summary='Create organization'),
    update=extend_schema(tags=['Organizations'], summary='Update organization'),
    partial_update=extend_schema(tags=['Organizations'], summary='Partially update organization'),
    destroy=extend_schema(tags=['Organizations'], summary='Delete organization'),
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

    @action(detail=True, methods=['get'])
    @extend_schema(tags=['Organizations'], summary='List organization members')
    def members(self, request, pk=None):
        organization = self.get_object()
        members = OrganizationMember.objects.filter(organization=organization).select_related(
            'user', 'job_role', 'organization'
        )
        return Response(OrganizationMemberSerializer(members, many=True).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'members/(?P<member_id>[^/.]+)/job-role',
    )
    @extend_schema(
        tags=['Organizations'],
        summary='Set a member job role (Backend, Frontend, DevOps, …)',
        request=OrganizationMemberJobRoleUpdateSerializer,
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
            member.job_role = JobRole.objects.get(pk=job_role_id)
        member.save(update_fields=['job_role', 'updated_at'])

        member = OrganizationMember.objects.select_related('user', 'job_role', 'organization').get(
            pk=member.pk
        )
        return Response(OrganizationMemberSerializer(member).data)


class OrganizationListForAuthenticatedView(viewsets.ReadOnlyModelViewSet):
    """Alias kept for tests that expect authenticated list without membership check on create."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()

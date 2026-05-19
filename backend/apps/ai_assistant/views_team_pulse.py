from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization

from .models import GitHubOrganizationConfig, TeamPulseReport
from .serializers_team_pulse import (
    DetailResponseSerializer,

    GitHubOrganizationConfigSerializer,
    GitHubOrganizationConfigWriteSerializer,
    TeamPulseReportSerializer,

    TeamPulseOverviewSerializer,

    TeamPulseRunQueuedSerializer,

    TeamPulseRunResponseSerializer,
    TeamPulseRunSerializer,
)
from .services.team_pulse import TeamPulseService
from .tasks_team_pulse import generate_organization_standup
from .views import OrganizationRAGMixin


@extend_schema(
    tags=['AI / Team Pulse'],
    parameters=[
        OpenApiParameter(
            name='organization_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Organization ID.',
        ),
    ],
    responses={
        200: TeamPulseOverviewSerializer,
        400: DetailResponseSerializer,
        403: DetailResponseSerializer,
    },
)
class TeamPulseOverviewView(OrganizationRAGMixin, APIView):
    """Latest standup report and GitHub config for an organization."""

    def get(self, request):
        organization_id = request.query_params.get('organization_id')
        if not organization_id:
            return Response({'detail': 'organization_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            organization_id = int(organization_id)
            self._assert_organization_access(request, organization_id)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid organization_id.'}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        github = GitHubOrganizationConfig.objects.filter(organization_id=organization_id).first()
        latest_standup = (
            TeamPulseReport.objects.filter(
                organization_id=organization_id,
                report_type=TeamPulseReport.ReportType.STANDUP,
            )
            .first()
        )

        return Response(
            {
                'github': GitHubOrganizationConfigSerializer(github).data if github else None,
                'latest_standup': (
                    TeamPulseReportSerializer(latest_standup).data if latest_standup else None
                ),
            }
        )


@extend_schema(
    tags=['AI / Team Pulse'],
    request=GitHubOrganizationConfigWriteSerializer,
    parameters=[
        OpenApiParameter(
            name='organization_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Organization ID for GET requests.',
        ),
    ],
    responses={
        200: GitHubOrganizationConfigSerializer,
        400: DetailResponseSerializer,
        403: DetailResponseSerializer,
        404: DetailResponseSerializer,
    },
)
class GitHubConfigView(OrganizationRAGMixin, APIView):
    def get(self, request):
        organization_id = request.query_params.get('organization_id')
        if not organization_id:
            return Response({'detail': 'organization_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            self._assert_organization_access(request, int(organization_id))
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        config = GitHubOrganizationConfig.objects.filter(organization_id=organization_id).first()
        if not config:
            return Response(None)
        return Response(GitHubOrganizationConfigSerializer(config).data)

    def put(self, request):
        serializer = GitHubOrganizationConfigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        organization_id = data['organization_id']
        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        organization = Organization.objects.filter(pk=organization_id).first()
        if not organization:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        config, _ = GitHubOrganizationConfig.objects.get_or_create(organization=organization)
        if 'repos' in data:
            config.repos = data['repos']
        if 'member_github_logins' in data:
            config.member_github_logins = {
                str(k): v for k, v in data['member_github_logins'].items()
            }
        if 'is_enabled' in data:
            config.is_enabled = data['is_enabled']
        token = data.get('access_token')
        if token:
            config.access_token = token
        config.save()

        return Response(GitHubOrganizationConfigSerializer(config).data)


@extend_schema(
    tags=['AI / Team Pulse'],
    request=TeamPulseRunSerializer,
    responses={
        200: TeamPulseRunResponseSerializer,
        202: TeamPulseRunQueuedSerializer,
        403: DetailResponseSerializer,
    },
)
class TeamPulseRunView(OrganizationRAGMixin, APIView):
    """Trigger daily standup manually."""

    def post(self, request):
        serializer = TeamPulseRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data['organization_id']

        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        from django.conf import settings

        service = TeamPulseService()
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            report = service.run_daily_standup(organization_id)
            return Response(
                {'standup': TeamPulseReportSerializer(report).data},
                status=status.HTTP_200_OK,
            )

        generate_organization_standup.delay(organization_id)
        return Response({'standup': 'queued'}, status=status.HTTP_202_ACCEPTED)

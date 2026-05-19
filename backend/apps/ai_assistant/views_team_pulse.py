from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.models import Workspace

from .models import GitHubWorkspaceConfig, TeamPulseAlert, TeamPulseReport
from .serializers_team_pulse import (
    GitHubWorkspaceConfigSerializer,
    GitHubWorkspaceConfigWriteSerializer,
    TeamPulseAlertSerializer,
    TeamPulseReportSerializer,
    TeamPulseRunSerializer,
)
from .services.team_pulse import TeamPulseService
from .tasks_team_pulse import analyze_workspace_workload, generate_workspace_standup
from .views import WorkspaceRAGMixin


class TeamPulseOverviewView(WorkspaceRAGMixin, APIView):
    """Latest standup, workload report, and active alerts for a workspace."""

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'detail': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            workspace_id = int(workspace_id)
            self._assert_workspace_access(request, workspace_id)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid workspace_id.'}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        github = GitHubWorkspaceConfig.objects.filter(workspace_id=workspace_id).first()
        alerts = TeamPulseAlert.objects.filter(
            workspace_id=workspace_id,
            is_dismissed=False,
        ).select_related('user', 'related_user')[:20]

        latest_standup = (
            TeamPulseReport.objects.filter(
                workspace_id=workspace_id,
                report_type=TeamPulseReport.ReportType.STANDUP,
            )
            .first()
        )
        latest_workload = (
            TeamPulseReport.objects.filter(
                workspace_id=workspace_id,
                report_type=TeamPulseReport.ReportType.WORKLOAD,
            )
            .first()
        )

        return Response(
            {
                'github': GitHubWorkspaceConfigSerializer(github).data if github else None,
                'alerts': TeamPulseAlertSerializer(alerts, many=True).data,
                'latest_standup': (
                    TeamPulseReportSerializer(latest_standup).data if latest_standup else None
                ),
                'latest_workload': (
                    TeamPulseReportSerializer(latest_workload).data if latest_workload else None
                ),
            }
        )


@extend_schema(tags=['AI / Team Pulse'], request=GitHubWorkspaceConfigWriteSerializer)
class GitHubConfigView(WorkspaceRAGMixin, APIView):
    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'detail': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            self._assert_workspace_access(request, int(workspace_id))
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        config = GitHubWorkspaceConfig.objects.filter(workspace_id=workspace_id).first()
        if not config:
            return Response(None)
        return Response(GitHubWorkspaceConfigSerializer(config).data)

    def put(self, request):
        serializer = GitHubWorkspaceConfigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workspace_id = data['workspace_id']
        try:
            self._assert_workspace_access(request, workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        workspace = Workspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            return Response({'detail': 'Workspace not found.'}, status=status.HTTP_404_NOT_FOUND)

        config, _ = GitHubWorkspaceConfig.objects.get_or_create(workspace=workspace)
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

        return Response(GitHubWorkspaceConfigSerializer(config).data)


@extend_schema(tags=['AI / Team Pulse'], request=TeamPulseRunSerializer)
class TeamPulseRunView(WorkspaceRAGMixin, APIView):
    """Trigger workload analysis and/or standup manually."""

    def post(self, request):
        serializer = TeamPulseRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace_id = serializer.validated_data['workspace_id']
        run_type = serializer.validated_data['run_type']

        try:
            self._assert_workspace_access(request, workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        service = TeamPulseService()
        results = {}

        if run_type in ('workload', 'both'):
            from django.conf import settings

            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                service.run_workload_analysis(workspace_id)
            else:
                analyze_workspace_workload.delay(workspace_id)
            results['workload'] = 'queued' if not settings.CELERY_TASK_ALWAYS_EAGER else 'completed'

        if run_type in ('standup', 'both'):
            from django.conf import settings

            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                report = service.run_daily_standup(workspace_id)
                results['standup'] = TeamPulseReportSerializer(report).data
            else:
                generate_workspace_standup.delay(workspace_id)
                results['standup'] = 'queued'

        return Response(results, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=['AI / Team Pulse'])
class TeamPulseDismissAlertView(WorkspaceRAGMixin, APIView):
    def post(self, request, alert_id: int):
        alert = TeamPulseAlert.objects.filter(pk=alert_id).select_related('workspace').first()
        if not alert:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            self._assert_workspace_access(request, alert.workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        alert.is_dismissed = True
        alert.save(update_fields=['is_dismissed', 'updated_at'])
        return Response({'ok': True})

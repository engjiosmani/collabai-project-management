"""Run workload analysis and daily standup for an organization."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from apps.ai_assistant.models import TeamPulseAlert, TeamPulseReport
from apps.notifications.models import Notification
from apps.organizations.models import Organization

from .standup import generate_standup_payload
from .workload import build_workload_alerts, compute_member_workloads

logger = logging.getLogger(__name__)


class TeamPulseService:
    def run_workload_analysis(self, organization_id: int) -> TeamPulseReport:
        workloads = compute_member_workloads(organization_id)
        alerts_data = build_workload_alerts(organization_id, workloads)

        TeamPulseAlert.objects.filter(
            organization_id=organization_id,
            is_dismissed=False,
            alert_type__in=[
                TeamPulseAlert.AlertType.BURNOUT_RISK,
                TeamPulseAlert.AlertType.CAPACITY_AVAILABLE,
                TeamPulseAlert.AlertType.REBALANCE_SUGGESTION,
            ],
        ).update(is_dismissed=True)

        for alert in alerts_data:
            TeamPulseAlert.objects.create(
                organization_id=organization_id,
                user_id=alert['user_id'],
                related_user_id=alert.get('related_user_id'),
                alert_type=alert['alert_type'],
                severity=alert['severity'],
                title=alert['title'],
                message=alert['message'],
                metrics=alert.get('metrics', {}),
            )
            self._notify_user(
                alert['user_id'],
                alert['title'],
                alert['message'],
            )

        now = timezone.now()
        summary_lines = ['## Workload snapshot', '']
        for w in workloads:
            summary_lines.append(
                f"- **{w.email}**: {w.active_tasks} active "
                f"({w.high_priority_tasks} high-pri), ~{w.estimated_hours}h, trend: {w.load_trend}"
            )

        report = TeamPulseReport.objects.create(
            organization_id=organization_id,
            report_type=TeamPulseReport.ReportType.WORKLOAD,
            summary_markdown='\n'.join(summary_lines),
            payload={
                'members': [w.__dict__ for w in workloads],
                'alerts_created': len(alerts_data),
            },
            period_start=now - timedelta(days=1),
            period_end=now,
        )
        logger.info('Workload analysis organization=%s alerts=%s', organization_id, len(alerts_data))
        return report

    def run_daily_standup(self, organization_id: int) -> TeamPulseReport:
        payload = generate_standup_payload(organization_id, hours=24)
        now = timezone.now()

        report = TeamPulseReport.objects.create(
            organization_id=organization_id,
            report_type=TeamPulseReport.ReportType.STANDUP,
            summary_markdown=payload.get('summary_markdown', ''),
            payload=payload,
            period_start=now - timedelta(hours=24),
            period_end=now,
        )

        logger.info(
            'Standup organization=%s members=%s',
            organization_id,
            len(payload.get('members', [])),
        )
        return report

    def _notify_user(self, user_id: int, title: str, message: str) -> None:
        try:
            Notification.objects.create(user_id=user_id, title=title, message=message)
        except Exception as exc:
            logger.warning('Could not create notification for user %s: %s', user_id, exc)

    @staticmethod
    def run_for_all_organizations(kind: str) -> int:
        count = 0
        for org in Organization.objects.all():
            service = TeamPulseService()
            if kind == 'workload':
                service.run_workload_analysis(org.pk)
            else:
                service.run_daily_standup(org.pk)
            count += 1
        return count

    @staticmethod
    def run_for_all_workspaces(kind: str) -> int:
        return TeamPulseService.run_for_all_organizations(kind)

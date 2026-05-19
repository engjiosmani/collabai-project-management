from __future__ import annotations

import logging

from celery import shared_task

from .services.team_pulse import TeamPulseService

logger = logging.getLogger(__name__)


@shared_task
def analyze_organization_workload(organization_id: int) -> int:
    TeamPulseService().run_workload_analysis(organization_id)
    return organization_id


@shared_task
def generate_organization_standup(organization_id: int) -> int:
    TeamPulseService().run_daily_standup(organization_id)
    return organization_id


analyze_workspace_workload = analyze_organization_workload
generate_workspace_standup = generate_organization_standup


@shared_task
def run_nightly_workload_analysis() -> int:
    return TeamPulseService.run_for_all_organizations('workload')


@shared_task
def run_daily_standup_agent() -> int:
    return TeamPulseService.run_for_all_organizations('standup')

from __future__ import annotations

import logging

from celery import shared_task

from .services.team_pulse import TeamPulseService

logger = logging.getLogger(__name__)


@shared_task
def analyze_workspace_workload(workspace_id: int) -> int:
    TeamPulseService().run_workload_analysis(workspace_id)
    return workspace_id


@shared_task
def generate_workspace_standup(workspace_id: int) -> int:
    TeamPulseService().run_daily_standup(workspace_id)
    return workspace_id


@shared_task
def run_nightly_workload_analysis() -> int:
    return TeamPulseService.run_for_all_workspaces('workload')


@shared_task
def run_daily_standup_agent() -> int:
    return TeamPulseService.run_for_all_workspaces('standup')

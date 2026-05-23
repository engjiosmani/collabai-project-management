from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.ai_assistant.services.team_pulse.workload import (
    DEFAULT_HOURS_PER_TASK,
    HIGH_PRIORITY_HOURS,
    MemberWorkload,
    _estimate_hours,
    _is_high_priority,
    _members_for_organization,
    build_workload_alerts,
    compute_member_workloads,
)


class WorkloadPriorityAndEstimateTests(SimpleTestCase):
    def test_is_high_priority_returns_false_without_priority_id(self):
        task = SimpleNamespace(priority_id=None, priority=None)

        self.assertFalse(_is_high_priority(task))

    def test_is_high_priority_detects_priority_name(self):
        for name in ("High", "Critical", "Urgent bug"):
            task = SimpleNamespace(
                priority_id=1,
                priority=SimpleNamespace(name=name, level=1),
            )

            self.assertTrue(_is_high_priority(task))

    def test_is_high_priority_detects_priority_level(self):
        task = SimpleNamespace(
            priority_id=1,
            priority=SimpleNamespace(name="Normal", level=3),
        )

        self.assertTrue(_is_high_priority(task))

    def test_is_high_priority_returns_false_for_low_priority(self):
        task = SimpleNamespace(
            priority_id=1,
            priority=SimpleNamespace(name="Low", level=1),
        )

        self.assertFalse(_is_high_priority(task))

    def test_estimate_hours_uses_default_hours_for_normal_task(self):
        task = SimpleNamespace(
            priority_id=None,
            priority=None,
            description="Small task",
        )

        self.assertEqual(_estimate_hours(task), DEFAULT_HOURS_PER_TASK)

    def test_estimate_hours_uses_high_priority_hours(self):
        task = SimpleNamespace(
            priority_id=1,
            priority=SimpleNamespace(name="Critical", level=1),
            description="Small task",
        )

        self.assertEqual(_estimate_hours(task), HIGH_PRIORITY_HOURS)

    def test_estimate_hours_adds_one_hour_for_long_description(self):
        task = SimpleNamespace(
            priority_id=None,
            priority=None,
            description="x" * 501,
        )

        self.assertEqual(_estimate_hours(task), DEFAULT_HOURS_PER_TASK + 1.0)

    def test_estimate_hours_current_code_adds_one_hour_for_very_long_description(self):
        task = SimpleNamespace(
            priority_id=None,
            priority=None,
            description="x" * 1600,
        )

        # Current implementation checks > 500 before > 1500, so very long
        # descriptions currently add 1 hour, not 2.
        self.assertEqual(_estimate_hours(task), DEFAULT_HOURS_PER_TASK + 1.0)


class QuerySetMock:
    def __init__(self, items=None, exists_value=None, count_value=None):
        self.items = list(items or [])
        self.exists_value = exists_value
        self.count_value = count_value

    def select_related(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def exclude(self, *args, **kwargs):
        return self

    def exists(self):
        if self.exists_value is not None:
            return self.exists_value
        return bool(self.items)

    def count(self):
        if self.count_value is not None:
            return self.count_value
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]


class MembersForOrganizationTests(SimpleTestCase):
    @patch("apps.ai_assistant.services.team_pulse.workload.TeamMember.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload.OrganizationMember.objects.filter")
    def test_members_for_organization_prefers_organization_members(
        self,
        org_filter,
        team_filter,
    ):
        org_members = QuerySetMock(items=[SimpleNamespace(user=SimpleNamespace())])
        org_filter.return_value = org_members

        result = _members_for_organization(organization_id=1)

        self.assertIs(result, org_members)
        org_filter.assert_called_once_with(organization_id=1)
        team_filter.assert_not_called()

    @patch("apps.ai_assistant.services.team_pulse.workload.TeamMember.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload.OrganizationMember.objects.filter")
    def test_members_for_organization_falls_back_to_team_members(
        self,
        org_filter,
        team_filter,
    ):
        org_filter.return_value = QuerySetMock(items=[], exists_value=False)
        team_members = QuerySetMock(items=[SimpleNamespace(user=SimpleNamespace())])
        team_filter.return_value = team_members

        result = _members_for_organization(organization_id=1)

        self.assertIs(result, team_members)
        team_filter.assert_called_once_with(workspace__organization_id=1)


class ComputeMemberWorkloadTests(SimpleTestCase):
    @patch("apps.ai_assistant.services.team_pulse.workload.ActivityLog.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload.Task.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload._members_for_organization")
    @patch("apps.ai_assistant.services.team_pulse.workload.completed_task_status_ids")
    def test_compute_member_workloads_builds_metrics(
        self,
        completed_status_ids,
        members_for_organization,
        task_filter,
        activity_filter,
    ):
        now = timezone.now()
        user = SimpleNamespace(
            pk=7,
            email="dev@example.com",
            get_username=lambda: "dev",
        )
        members_for_organization.return_value = [SimpleNamespace(user=user)]
        completed_status_ids.return_value = [3]

        active_normal = SimpleNamespace(
            priority_id=None,
            priority=None,
            description="normal",
        )
        active_high = SimpleNamespace(
            priority_id=1,
            priority=SimpleNamespace(name="High", level=1),
            description="x" * 501,
        )

        tasks_qs = MagicMock()
        tasks_qs.exclude.return_value = [active_normal, active_high]
        tasks_qs.filter.side_effect = [
            QuerySetMock(count_value=4),
            QuerySetMock(count_value=1),
        ]
        task_filter.return_value.select_related.return_value = tasks_qs

        completed_task = SimpleNamespace(created_at=now - timedelta(hours=10))
        completed_log = SimpleNamespace(
            description="Status changed to Done",
            created_at=now,
            task=completed_task,
        )
        activity_filter.return_value.select_related.return_value = QuerySetMock(
            items=[completed_log]
        )

        result = compute_member_workloads(organization_id=5)

        self.assertEqual(len(result), 1)
        workload = result[0]

        self.assertEqual(workload.user_id, 7)
        self.assertEqual(workload.email, "dev@example.com")
        self.assertEqual(workload.active_tasks, 2)
        self.assertEqual(workload.high_priority_tasks, 1)
        self.assertEqual(workload.estimated_hours, 7.0)
        self.assertEqual(workload.avg_completion_hours, 10.0)
        self.assertEqual(workload.completed_last_7d, 4)
        self.assertEqual(workload.completed_prev_7d, 1)
        self.assertEqual(workload.load_trend, "increasing")

    @patch("apps.ai_assistant.services.team_pulse.workload.ActivityLog.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload.Task.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload._members_for_organization")
    @patch("apps.ai_assistant.services.team_pulse.workload.completed_task_status_ids")
    def test_compute_member_workloads_skips_member_without_user(
        self,
        completed_status_ids,
        members_for_organization,
        task_filter,
        activity_filter,
    ):
        completed_status_ids.return_value = [3]
        members_for_organization.return_value = [SimpleNamespace(user=None)]

        result = compute_member_workloads(organization_id=5)

        self.assertEqual(result, [])
        task_filter.assert_not_called()
        activity_filter.assert_not_called()

    @patch("apps.ai_assistant.services.team_pulse.workload.ActivityLog.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload.Task.objects.filter")
    @patch("apps.ai_assistant.services.team_pulse.workload._members_for_organization")
    @patch("apps.ai_assistant.services.team_pulse.workload.completed_task_status_ids")
    def test_compute_member_workloads_handles_no_done_statuses_and_decreasing_trend(
        self,
        completed_status_ids,
        members_for_organization,
        task_filter,
        activity_filter,
    ):
        user = SimpleNamespace(
            pk=8,
            email="",
            get_username=lambda: "fallback-user",
        )
        members_for_organization.return_value = [SimpleNamespace(user=user)]
        completed_status_ids.return_value = []

        tasks_qs = MagicMock()
        tasks_qs.__iter__.return_value = iter([])
        task_filter.return_value.select_related.return_value = tasks_qs
        activity_filter.return_value.select_related.return_value = QuerySetMock(items=[])

        result = compute_member_workloads(organization_id=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].email, "fallback-user")
        self.assertEqual(result[0].active_tasks, 0)
        self.assertEqual(result[0].completed_last_7d, 0)
        self.assertEqual(result[0].completed_prev_7d, 0)
        self.assertEqual(result[0].load_trend, "stable")


class BuildWorkloadAlertsTests(SimpleTestCase):
    def test_build_workload_alerts_creates_burnout_capacity_and_rebalance(self):
        overloaded = MemberWorkload(
            user_id=1,
            email="over@example.com",
            active_tasks=10,
            high_priority_tasks=4,
            estimated_hours=30.0,
            avg_completion_hours=5.0,
            load_trend="increasing",
            completed_last_7d=5,
            completed_prev_7d=1,
        )
        underloaded = MemberWorkload(
            user_id=2,
            email="under@example.com",
            active_tasks=2,
            high_priority_tasks=0,
            estimated_hours=4.0,
            avg_completion_hours=None,
            load_trend="stable",
            completed_last_7d=1,
            completed_prev_7d=1,
        )

        alerts = build_workload_alerts(
            organization_id=99,
            workloads=[overloaded, underloaded],
        )

        alert_types = [alert["alert_type"] for alert in alerts]

        self.assertIn("burnout_risk", alert_types)
        self.assertIn("capacity_available", alert_types)
        self.assertIn("rebalance_suggestion", alert_types)

        burnout = next(a for a in alerts if a["alert_type"] == "burnout_risk")
        self.assertEqual(burnout["user_id"], 1)
        self.assertEqual(burnout["severity"], "warning")
        self.assertIn("over may be overloaded", burnout["title"])
        self.assertEqual(burnout["metrics"], overloaded.__dict__)

        capacity = next(a for a in alerts if a["alert_type"] == "capacity_available")
        self.assertEqual(capacity["user_id"], 2)
        self.assertEqual(capacity["severity"], "suggestion")
        self.assertIn("under has capacity", capacity["title"])

        rebalance = next(a for a in alerts if a["alert_type"] == "rebalance_suggestion")
        self.assertEqual(rebalance["user_id"], 1)
        self.assertEqual(rebalance["related_user_id"], 2)
        self.assertEqual(rebalance["metrics"]["suggested_moves"], 3)

    def test_build_workload_alerts_only_capacity_for_underloaded_member(self):
        underloaded = MemberWorkload(
            user_id=2,
            email="under@example.com",
            active_tasks=3,
            high_priority_tasks=0,
            estimated_hours=6.0,
            avg_completion_hours=None,
            load_trend="stable",
            completed_last_7d=1,
            completed_prev_7d=1,
        )

        alerts = build_workload_alerts(
            organization_id=99,
            workloads=[underloaded],
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["alert_type"], "capacity_available")

    def test_build_workload_alerts_no_burnout_when_only_moderately_overloaded(self):
        moderate = MemberWorkload(
            user_id=3,
            email="moderate@example.com",
            active_tasks=8,
            high_priority_tasks=1,
            estimated_hours=16.0,
            avg_completion_hours=None,
            load_trend="stable",
            completed_last_7d=1,
            completed_prev_7d=1,
        )

        alerts = build_workload_alerts(
            organization_id=99,
            workloads=[moderate],
        )

        self.assertEqual(alerts, [])

    def test_build_workload_alerts_skips_rebalance_to_same_user(self):
        workload = MemberWorkload(
            user_id=1,
            email="same@example.com",
            active_tasks=10,
            high_priority_tasks=4,
            estimated_hours=30.0,
            avg_completion_hours=None,
            load_trend="stable",
            completed_last_7d=1,
            completed_prev_7d=1,
        )

        alerts = build_workload_alerts(
            organization_id=99,
            workloads=[workload],
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["alert_type"], "burnout_risk")
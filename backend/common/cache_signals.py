"""Shared cache invalidation hooks for cross-cutting read models."""
from common.cache import (
    NAMESPACE_ACTIVITY_LOGS,
    NAMESPACE_COMMENTS,
    NAMESPACE_DASHBOARD,
    NAMESPACE_METRICS,
    NAMESPACE_NOTIFICATIONS,
    NAMESPACE_ORGANIZATIONS,
    NAMESPACE_PROJECTS,
    NAMESPACE_TASKS,
    NAMESPACE_WORKSPACES,
    bump_dashboard_cache,
    bump_version,
)


def _bump_metrics_cache() -> None:
    bump_version(NAMESPACE_METRICS)


def invalidate_after_project_change() -> None:
    bump_version(NAMESPACE_PROJECTS)
    bump_version(NAMESPACE_WORKSPACES)
    bump_dashboard_cache()
    _bump_metrics_cache()


def invalidate_after_task_change() -> None:
    bump_version(NAMESPACE_TASKS)
    bump_version(NAMESPACE_ACTIVITY_LOGS)
    bump_version(NAMESPACE_COMMENTS)
    bump_dashboard_cache()
    _bump_metrics_cache()


def invalidate_after_workspace_change() -> None:
    bump_version(NAMESPACE_WORKSPACES)
    bump_version(NAMESPACE_ORGANIZATIONS)
    bump_dashboard_cache()
    _bump_metrics_cache()


def invalidate_after_organization_change() -> None:
    bump_version(NAMESPACE_ORGANIZATIONS)
    bump_dashboard_cache()
    _bump_metrics_cache()


def invalidate_after_comment_change() -> None:
    bump_version(NAMESPACE_COMMENTS)
    bump_version(NAMESPACE_ACTIVITY_LOGS)
    bump_dashboard_cache()
    _bump_metrics_cache()


def invalidate_after_notification_change() -> None:
    bump_version(NAMESPACE_NOTIFICATIONS)
    _bump_metrics_cache()


def invalidate_after_activity_log_change() -> None:
    bump_version(NAMESPACE_ACTIVITY_LOGS)
    bump_dashboard_cache()
    _bump_metrics_cache()

"""Deprecated module — use common.tenant_access."""

from common.tenant_access import (  # noqa: F401
    organizations_queryset_for_user,
    resolve_organization,
    resolve_workspace,
    user_can_access_organization,
    user_can_access_workspace,
    workspaces_queryset_for_user,
)

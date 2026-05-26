from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_organizations(self, organization_ids):
        if not organization_ids:
            return self.none()

        if hasattr(self.model, 'organization_id'):
            return self.filter(organization_id__in=organization_ids)

        if hasattr(self.model, 'project_id'):
            return self.filter(project__organization_id__in=organization_ids)

        if hasattr(self.model, 'task_id'):
            return self.filter(task__project__organization_id__in=organization_ids)

        return self.none()

    def for_workspaces(self, workspace_ids):
        """Compatibility wrapper for older workspace-scoped call sites."""
        return self.for_organizations(workspace_ids)

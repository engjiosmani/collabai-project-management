from django.db import models


class TenantQuerySet(models.QuerySet):

    def for_workspaces(self, workspace_ids):

        return self.filter(
            workspace_id__in=workspace_ids
        )
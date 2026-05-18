from rest_framework import viewsets


class TenantScopedViewSet(viewsets.ModelViewSet):

    workspace_field = "workspace"

    def get_queryset(self):

        return self.queryset.for_workspaces(
            getattr(self.request, "workspace_ids", [])
        )
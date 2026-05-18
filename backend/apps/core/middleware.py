from common.workspace_access import workspaces_queryset_for_user


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.workspace_ids = []
        request.workspace = None

        if request.user.is_authenticated:

            workspaces = workspaces_queryset_for_user(
                request.user
            )

            request.workspace_ids = list(
                workspaces.values_list("id", flat=True)
            )

            request.workspace = workspaces.first()

        response = self.get_response(request)

        return response
from common.workspace_access import workspaces_queryset_for_user


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.workspace_ids = []

        if request.user.is_authenticated:

            request.workspace_ids = list(
                workspaces_queryset_for_user(
                    request.user
                ).values_list("id", flat=True)
            )

        response = self.get_response(request)

        return response
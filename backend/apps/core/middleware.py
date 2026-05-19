from common.tenant_access import organizations_queryset_for_user


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization_ids = []
        request.organization = None
        # Legacy attribute kept empty so old code paths fail fast if still referenced
        request.workspace_ids = []
        request.workspace = None

        if request.user.is_authenticated:
            orgs = organizations_queryset_for_user(request.user)
            request.organization_ids = list(orgs.values_list('id', flat=True))
            request.organization = orgs.first()

        response = self.get_response(request)
        return response

from common.tenant_access import active_organization_id_from_request, organizations_queryset_for_user


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization_ids = []
        request.organization = None
        request.requested_organization_id = None
        request.invalid_requested_organization_id = False
        request.active_organization_id = None
        request.active_organization = None
        # Legacy attribute kept empty so old code paths fail fast if still referenced
        request.workspace_ids = []
        request.workspace = None

        if request.user.is_authenticated:
            orgs = organizations_queryset_for_user(request.user).order_by('id')
            request.organization_ids = list(orgs.values_list('id', flat=True))
            requested_org_id = active_organization_id_from_request(request)
            request.requested_organization_id = requested_org_id if requested_org_id in request.organization_ids else None
            request.invalid_requested_organization_id = requested_org_id is not None and requested_org_id not in request.organization_ids
            active_org = None
            if requested_org_id in request.organization_ids:
                active_org = orgs.filter(pk=requested_org_id).first()
            if active_org is None:
                active_org = orgs.first()
            request.organization = active_org
            request.active_organization = active_org
            request.active_organization_id = active_org.pk if active_org else None

        response = self.get_response(request)
        return response

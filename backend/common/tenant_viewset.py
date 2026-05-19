from rest_framework import viewsets


class TenantScopedViewSet(viewsets.ModelViewSet):
    organization_field = 'organization'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()

        org_ids = getattr(self.request, 'organization_ids', [])
        field = self.organization_field
        if field == 'organization':
            return self.queryset.filter(organization_id__in=org_ids)
        return self.queryset.filter(**{f'{field}__organization_id__in': org_ids})

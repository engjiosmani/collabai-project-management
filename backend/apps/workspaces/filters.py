import django_filters

from .models import Workspace


class WorkspaceFilter(django_filters.FilterSet):
    organization_id = django_filters.NumberFilter(
        field_name='organization_id',
        label='Organization ID'
    )
    is_active = django_filters.BooleanFilter(field_name='is_active')

    class Meta:
        model = Workspace
        fields = ('organization_id', 'is_active')
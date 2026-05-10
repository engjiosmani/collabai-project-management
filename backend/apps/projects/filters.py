import django_filters

from .models import Project


class ProjectFilter(django_filters.FilterSet):
    organization = django_filters.NumberFilter(field_name='workspace__organization_id')
    workspace = django_filters.NumberFilter(field_name='workspace_id')
    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')
    start_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    due_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')

    class Meta:
        model = Project
        fields = ('is_active', 'workspace', 'organization')
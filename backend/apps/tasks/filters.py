import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    project = django_filters.NumberFilter(field_name='project_id')
    workspace = django_filters.NumberFilter(field_name='project__workspace_id')
    organization = django_filters.NumberFilter(field_name='project__workspace__organization_id')
    status = django_filters.NumberFilter(field_name='status_id')
    priority = django_filters.NumberFilter(field_name='priority_id')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')
    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')
    due_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')

    class Meta:
        model = Task
        fields = ('project', 'workspace', 'organization', 'status', 'priority', 'assigned_to')
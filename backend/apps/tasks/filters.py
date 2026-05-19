import django_filters

from common.filtering import filter_id_or_name

from .models import Task


class TaskFilter(django_filters.FilterSet):
    project = django_filters.NumberFilter(field_name='project_id')
    organization = django_filters.NumberFilter(field_name='project__organization_id')
    status = django_filters.CharFilter(method='filter_status')
    priority = django_filters.CharFilter(method='filter_priority')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to_id')
    assignee = django_filters.NumberFilter(field_name='assigned_to_id')
    label = django_filters.CharFilter(method='filter_label')
    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')
    due_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')

    class Meta:
        model = Task
        fields = (
            'project',
            'organization',
            'status',
            'priority',
            'assigned_to',
            'assignee',
            'label',
        )

    def filter_status(self, queryset, name, value):
        return filter_id_or_name(queryset, id_field='status_id', name_field='status__name', value=value)

    def filter_priority(self, queryset, name, value):
        return filter_id_or_name(queryset, id_field='priority_id', name_field='priority__name', value=value)

    def filter_label(self, queryset, name, value):
        return filter_id_or_name(queryset, id_field='task_labels__label_id', name_field='task_labels__label__name', value=value)

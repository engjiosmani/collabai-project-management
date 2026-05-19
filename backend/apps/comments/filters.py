import django_filters

from .models import ActivityLog, Comment


class CommentFilter(django_filters.FilterSet):
    task = django_filters.NumberFilter(field_name='task_id')
    project = django_filters.NumberFilter(field_name='task__project_id')
    organization = django_filters.NumberFilter(field_name='task__project__organization_id')
    author = django_filters.NumberFilter(field_name='author_id')
    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Comment
        fields = ('task', 'project', 'organization', 'author')


class ActivityLogFilter(django_filters.FilterSet):
    task = django_filters.NumberFilter(field_name='task_id')
    project = django_filters.NumberFilter(field_name='task__project_id')
    organization = django_filters.NumberFilter(field_name='task__project__organization_id')
    user = django_filters.NumberFilter(field_name='user_id')
    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = ActivityLog
        fields = ('task', 'project', 'organization', 'user')

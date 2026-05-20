import django_filters

from .models import Permission, Role, Workspace


class WorkspaceFilter(django_filters.FilterSet):
    organization = django_filters.NumberFilter(field_name='organization_id')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    created_after = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    class Meta:
        model = Workspace
        fields = ('organization', 'is_active')


class RoleFilter(django_filters.FilterSet):
    workspace = django_filters.NumberFilter(field_name='workspace_id')
    created_after = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    class Meta:
        model = Role
        fields = ('workspace',)


class PermissionFilter(django_filters.FilterSet):
    code = django_filters.CharFilter(field_name='code', lookup_expr='icontains')
    created_after = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    class Meta:
        model = Permission
        fields = ('code',)
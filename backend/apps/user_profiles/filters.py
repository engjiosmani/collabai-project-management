import django_filters
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    workspace = django_filters.NumberFilter(field_name='profile__workspace_id')
    role = django_filters.NumberFilter(field_name='profile__role_id')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    email = django_filters.CharFilter(field_name='email', lookup_expr='icontains')

    class Meta:
        model = User
        fields = ('workspace', 'role', 'is_active', 'email')



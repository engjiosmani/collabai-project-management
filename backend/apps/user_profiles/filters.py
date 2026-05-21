import django_filters
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    organization = django_filters.NumberFilter(field_name='profile__organization_id')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    email = django_filters.CharFilter(field_name='email', lookup_expr='icontains')

    class Meta:
        model = User
        fields = ('organization', 'is_active', 'email')
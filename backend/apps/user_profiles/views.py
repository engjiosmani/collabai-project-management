from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.tenant_access import organizations_queryset_for_user

from .filters import UserFilter
from .serializers import UserMeSerializer, UserSerializer

User = get_user_model()


@extend_schema_view(
    list=extend_schema(tags=['Users'], summary='List users'),
    retrieve=extend_schema(tags=['Users'], summary='Retrieve user'),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = UserFilter
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering_fields = ('date_joined', 'email', 'username', 'first_name', 'last_name')
    ordering = ('email',)

    def get_queryset(self) -> QuerySet[User]:
        """
		Get users that are members of organizations the current user belongs to.

		For superusers: all users
		For regular users: users in the same organizations + self
		"""
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        user = self.request.user

        if getattr(user, 'is_superuser', False):
            return User.objects.all().select_related('profile', 'profile__organization').order_by('email')

        # Get all organizations the user belongs to
        org_ids = organizations_queryset_for_user(user).values_list('pk', flat=True)

        # Return users who are members of same organizations + self
        return (
            User.objects.filter(Q(organization_memberships__organization_id__in=org_ids) | Q(pk=user.pk))
            .distinct()
            .select_related('profile', 'profile__organization')
            .order_by('email')
        )

    def get_serializer_class(self):
        if self.action == 'me':
            return UserMeSerializer
        return UserSerializer

    @extend_schema(tags=['Users'], summary='Get or update the current user')
    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        serializer = self.get_serializer(request.user, data=request.data if request.method == 'PATCH' else None,
                                         partial=True)
        if request.method == 'PATCH':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserSerializer(request.user, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(UserSerializer(request.user, context={'request': request}).data, status=status.HTTP_200_OK)
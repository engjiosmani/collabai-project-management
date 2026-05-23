from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.organizations.models import OrganizationMember
from common.tenant_access import organization_ids_for_request, organizations_queryset_for_user
from .filters import UserFilter
from .serializers import (
    ChangePasswordSerializer,
    MembershipSerializer,
    ProfileDetailSerializer,
    UserMeSerializer,
    UserSerializer,
)
User = get_user_model()
# ── Existing UserViewSet (unchanged) ─────────────────────────────────────────
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
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        user = self.request.user
        if getattr(user, 'is_superuser', False):
            return User.objects.all().select_related('profile', 'profile__organization').order_by('email')
        org_ids = organization_ids_for_request(self.request)
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
        serializer = self.get_serializer(
            request.user,
            data=request.data if request.method == 'PATCH' else None,
            partial=True,
        )
        if request.method == 'PATCH':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                UserSerializer(request.user, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )
        return Response(
            UserSerializer(request.user, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
# ── AUTH-03 profile views ─────────────────────────────────────────────────────
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Profile'],
        summary='Get current user profile',
        responses={200: ProfileDetailSerializer},
    )
    def get(self, request):
        serializer = ProfileDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    @extend_schema(
        tags=['Profile'],
        summary='Update current user profile (name, bio, phone, avatar)',
        request=ProfileDetailSerializer,
        responses={200: ProfileDetailSerializer},
    )
    def patch(self, request):
        serializer = ProfileDetailSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ProfileDetailSerializer(request.user, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Profile'],
        summary='Change password (requires old_password, new_password, confirm_password)',
        request=ChangePasswordSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)
class MembershipsView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Profile'],
        summary='List all organizations and workspaces the current user belongs to',
        responses={200: MembershipSerializer(many=True)},
    )
    def get(self, request):
        org_memberships = (
            OrganizationMember.objects.filter(user=request.user)
            .select_related('organization', 'user')
        )
        serializer = MembershipSerializer(org_memberships, many=True)
        return Response(serializer.data)


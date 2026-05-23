from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework import status

from apps.user_profiles.views import (
    ChangePasswordView,
    MembershipsView,
    ProfileView,
    UserViewSet,
)

User = get_user_model()


class UserProfilesViewsUnitTests(SimpleTestCase):
    def test_user_viewset_get_queryset_returns_none_for_swagger_fake_view(self):
        view = UserViewSet()
        view.swagger_fake_view = True

        qs = view.get_queryset()

        self.assertEqual(qs.count(), 0)

    @patch("apps.user_profiles.views.organizations_queryset_for_user")
    @patch("apps.user_profiles.views.User.objects")
    def test_user_viewset_get_queryset_for_superuser(self, user_objects, orgs_for_user):
        view = UserViewSet()
        view.request = SimpleNamespace(user=SimpleNamespace(is_superuser=True))

        ordered_qs = MagicMock()
        selected_qs = MagicMock()
        all_qs = MagicMock()
        all_qs.select_related.return_value = selected_qs
        selected_qs.order_by.return_value = ordered_qs
        user_objects.all.return_value = all_qs

        result = view.get_queryset()

        self.assertIs(result, ordered_qs)
        user_objects.all.assert_called_once()
        all_qs.select_related.assert_called_once_with(
            "profile",
            "profile__organization",
        )
        selected_qs.order_by.assert_called_once_with("email")
        orgs_for_user.assert_not_called()

    @patch("apps.user_profiles.views.organizations_queryset_for_user")
    @patch("apps.user_profiles.views.User.objects")
    def test_user_viewset_get_queryset_for_normal_user(self, user_objects, orgs_for_user):
        user = SimpleNamespace(pk=7, is_superuser=False)
        view = UserViewSet()
        view.request = SimpleNamespace(user=user)

        org_ids = MagicMock()
        orgs_for_user.return_value.values_list.return_value = org_ids

        filter_qs = MagicMock()
        distinct_qs = MagicMock()
        selected_qs = MagicMock()
        ordered_qs = MagicMock()

        user_objects.filter.return_value = filter_qs
        filter_qs.distinct.return_value = distinct_qs
        distinct_qs.select_related.return_value = selected_qs
        selected_qs.order_by.return_value = ordered_qs

        result = view.get_queryset()

        self.assertIs(result, ordered_qs)
        orgs_for_user.assert_called_once_with(user)
        orgs_for_user.return_value.values_list.assert_called_once_with("pk", flat=True)
        user_objects.filter.assert_called_once()
        filter_qs.distinct.assert_called_once()
        distinct_qs.select_related.assert_called_once_with(
            "profile",
            "profile__organization",
        )
        selected_qs.order_by.assert_called_once_with("email")

    def test_get_serializer_class_uses_user_me_for_me_action(self):
        view = UserViewSet()
        view.action = "me"

        self.assertEqual(view.get_serializer_class().__name__, "UserMeSerializer")

    def test_get_serializer_class_uses_default_user_serializer(self):
        view = UserViewSet()
        view.action = "list"

        self.assertEqual(view.get_serializer_class().__name__, "UserSerializer")

    def test_me_get_returns_current_user_data(self):
        view = UserViewSet()
        request = SimpleNamespace(method="GET", user=SimpleNamespace(id=1), data={})

        with patch.object(view, "get_serializer") as get_serializer, patch(
            "apps.user_profiles.views.UserSerializer"
        ) as user_serializer_cls:
            serializer = MagicMock()
            get_serializer.return_value = serializer
            user_serializer = MagicMock()
            user_serializer.data = {"id": 1}
            user_serializer_cls.return_value = user_serializer

            response = view.me(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"id": 1})
        serializer.is_valid.assert_not_called()
        user_serializer_cls.assert_called_once()

    def test_me_patch_validates_saves_and_returns_current_user_data(self):
        view = UserViewSet()
        request = SimpleNamespace(
            method="PATCH",
            user=SimpleNamespace(id=1),
            data={"first_name": "Leona"},
        )

        with patch.object(view, "get_serializer") as get_serializer, patch(
            "apps.user_profiles.views.UserSerializer"
        ) as user_serializer_cls:
            serializer = MagicMock()
            get_serializer.return_value = serializer
            user_serializer = MagicMock()
            user_serializer.data = {"id": 1, "first_name": "Leona"}
            user_serializer_cls.return_value = user_serializer

            response = view.me(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"id": 1, "first_name": "Leona"})
        serializer.is_valid.assert_called_once_with(raise_exception=True)
        serializer.save.assert_called_once()

    def test_profile_get_returns_profile_detail_data(self):
        request = SimpleNamespace(user=SimpleNamespace(id=1))

        with patch("apps.user_profiles.views.ProfileDetailSerializer") as serializer_cls:
            serializer = MagicMock()
            serializer.data = {"email": "user@example.com"}
            serializer_cls.return_value = serializer

            response = ProfileView().get(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"email": "user@example.com"})

    def test_profile_patch_validates_saves_and_returns_updated_data(self):
        request = SimpleNamespace(
            user=SimpleNamespace(id=1),
            data={"bio": "Updated"},
        )

        with patch("apps.user_profiles.views.ProfileDetailSerializer") as serializer_cls:
            update_serializer = MagicMock()
            response_serializer = MagicMock()
            response_serializer.data = {"bio": "Updated"}
            serializer_cls.side_effect = [update_serializer, response_serializer]

            response = ProfileView().patch(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"bio": "Updated"})
        update_serializer.is_valid.assert_called_once_with(raise_exception=True)
        update_serializer.save.assert_called_once()

    def test_change_password_post_sets_password_and_saves_user(self):
        user = MagicMock()
        request = SimpleNamespace(
            user=user,
            data={
                "old_password": "old",
                "new_password": "new-password",
                "confirm_password": "new-password",
            },
        )

        with patch("apps.user_profiles.views.ChangePasswordSerializer") as serializer_cls:
            serializer = MagicMock()
            serializer.validated_data = {"new_password": "new-password"}
            serializer_cls.return_value = serializer

            response = ChangePasswordView().post(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Password updated successfully.")
        serializer.is_valid.assert_called_once_with(raise_exception=True)
        user.set_password.assert_called_once_with("new-password")
        user.save.assert_called_once()

    @patch("apps.user_profiles.views.OrganizationMember.objects.filter")
    @patch("apps.user_profiles.views.MembershipSerializer")
    def test_memberships_get_returns_membership_data(self, serializer_cls, member_filter):
        request = SimpleNamespace(user=SimpleNamespace(id=1))

        memberships = MagicMock()
        member_filter.return_value.select_related.return_value = memberships

        serializer = MagicMock()
        serializer.data = [{"organization": {"id": 1}}]
        serializer_cls.return_value = serializer

        response = MembershipsView().get(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"organization": {"id": 1}}])
        member_filter.assert_called_once_with(user=request.user)
        member_filter.return_value.select_related.assert_called_once_with(
            "organization",
            "user",
        )
        serializer_cls.assert_called_once_with(memberships, many=True)
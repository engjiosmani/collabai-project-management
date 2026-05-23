from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework import status

from apps.projects.views import ProjectViewSet

User = get_user_model()


class ProjectViewSetUnitTests(SimpleTestCase):
    def test_get_queryset_returns_none_when_request_has_no_organization_ids(self):
        view = ProjectViewSet()
        view.request = SimpleNamespace(
            organization_ids=[],
            user=SimpleNamespace(is_authenticated=True),
        )

        base_queryset = MagicMock()
        none_queryset = MagicMock()
        base_queryset.none.return_value = none_queryset

        with patch(
            "common.tenant_viewset.TenantScopedViewSet.get_queryset",
            return_value=base_queryset,
        ):
            result = view.get_queryset()

        self.assertIs(result, none_queryset)
        base_queryset.none.assert_called_once()

    def test_get_queryset_filters_by_project_visibility_when_org_ids_exist(self):
        view = ProjectViewSet()
        user = SimpleNamespace(is_authenticated=True)
        view.request = SimpleNamespace(
            organization_ids=[1, 2],
            user=user,
        )

        base_queryset = MagicMock()
        filtered_queryset = MagicMock()
        distinct_queryset = MagicMock()
        base_queryset.filter.return_value = filtered_queryset
        filtered_queryset.distinct.return_value = distinct_queryset

        with patch(
            "common.tenant_viewset.TenantScopedViewSet.get_queryset",
            return_value=base_queryset,
        ), patch("apps.projects.views.project_visibility_q", return_value="visibility-q") as visibility_q:
            result = view.get_queryset()

        self.assertIs(result, distinct_queryset)
        visibility_q.assert_called_once_with(user, [1, 2])
        base_queryset.filter.assert_called_once_with("visibility-q")
        filtered_queryset.distinct.assert_called_once()

    def test_get_permissions_destroy_uses_admin_permission(self):
        view = ProjectViewSet()
        view.action = "destroy"

        permissions = view.get_permissions()

        self.assertEqual(len(permissions), 1)
        self.assertEqual(permissions[0].__class__.__name__, "IsOrgAdmin")

    def test_get_permissions_update_uses_manager_or_admin_permission(self):
        for action in ("update", "partial_update"):
            view = ProjectViewSet()
            view.action = action

            permissions = view.get_permissions()

            self.assertEqual(len(permissions), 1)
            self.assertEqual(permissions[0].__class__.__name__, "IsManagerOrAbove")

    @patch("apps.projects.views.ProjectMemberSerializer")
    @patch("apps.projects.views.ProjectMember.objects.filter")
    def test_members_get_returns_project_members(self, member_filter, serializer_cls):
        view = ProjectViewSet()
        project = SimpleNamespace(id=1)
        view.get_object = MagicMock(return_value=project)

        request = SimpleNamespace(method="GET")
        members_qs = MagicMock()
        member_filter.return_value.select_related.return_value = members_qs
        serializer = MagicMock()
        serializer.data = [{"id": 1}]
        serializer_cls.return_value = serializer

        response = view.members(request, pk=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"id": 1}])
        member_filter.assert_called_once_with(project=project)
        member_filter.return_value.select_related.assert_called_once_with("user")
        serializer_cls.assert_called_once_with(members_qs, many=True)

    @patch("apps.projects.views.ProjectMemberSerializer")
    @patch("apps.projects.views.ProjectMember.objects.get_or_create")
    @patch("apps.projects.views.User.objects.get")
    @patch("apps.projects.views.AddProjectMemberSerializer")
    def test_members_post_adds_new_project_member(
        self,
        add_serializer_cls,
        user_get,
        get_or_create,
        member_serializer_cls,
    ):
        view = ProjectViewSet()
        project = SimpleNamespace(id=1)
        user = SimpleNamespace(id=2)
        member = SimpleNamespace(project=project, user=user)

        view.get_object = MagicMock(return_value=project)
        request = SimpleNamespace(method="POST", data={"user_id": 2})

        serializer = MagicMock()
        serializer.validated_data = {"user_id": 2}
        add_serializer_cls.return_value = serializer

        user_get.return_value = user
        get_or_create.return_value = (member, True)

        member_serializer = MagicMock()
        member_serializer.data = {"user": 2}
        member_serializer_cls.return_value = member_serializer

        response = view.members(request, pk=1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"user": 2})
        serializer.is_valid.assert_called_once_with(raise_exception=True)
        user_get.assert_called_once_with(pk=2)
        get_or_create.assert_called_once_with(project=project, user=user)
        member_serializer_cls.assert_called_once_with(member)

    @patch("apps.projects.views.ProjectMemberSerializer")
    @patch("apps.projects.views.ProjectMember.objects.get_or_create")
    @patch("apps.projects.views.User.objects.get")
    @patch("apps.projects.views.AddProjectMemberSerializer")
    def test_members_post_existing_project_member_returns_200(
        self,
        add_serializer_cls,
        user_get,
        get_or_create,
        member_serializer_cls,
    ):
        view = ProjectViewSet()
        project = SimpleNamespace(id=1)
        user = SimpleNamespace(id=2)
        member = SimpleNamespace(project=project, user=user)

        view.get_object = MagicMock(return_value=project)
        request = SimpleNamespace(method="POST", data={"user_id": 2})

        serializer = MagicMock()
        serializer.validated_data = {"user_id": 2}
        add_serializer_cls.return_value = serializer

        user_get.return_value = user
        get_or_create.return_value = (member, False)

        member_serializer = MagicMock()
        member_serializer.data = {"user": 2}
        member_serializer_cls.return_value = member_serializer

        response = view.members(request, pk=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"user": 2})

    @patch("apps.projects.views.ProjectMember.objects.filter")
    def test_remove_member_returns_404_when_member_not_found(self, member_filter):
        view = ProjectViewSet()
        project = SimpleNamespace(id=1)
        view.get_object = MagicMock(return_value=project)

        qs = MagicMock()
        qs.delete.return_value = (0, {})
        member_filter.return_value = qs

        response = view.remove_member(
            SimpleNamespace(method="DELETE"),
            pk=1,
            user_id=99,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Member not found.")
        member_filter.assert_called_once_with(project=project, user_id=99)

    @patch("apps.projects.views.ProjectMember.objects.filter")
    def test_remove_member_returns_204_when_member_deleted(self, member_filter):
        view = ProjectViewSet()
        project = SimpleNamespace(id=1)
        view.get_object = MagicMock(return_value=project)

        qs = MagicMock()
        qs.delete.return_value = (1, {"projects.ProjectMember": 1})
        member_filter.return_value = qs

        response = view.remove_member(
            SimpleNamespace(method="DELETE"),
            pk=1,
            user_id=99,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

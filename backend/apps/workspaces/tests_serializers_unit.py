from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase
from rest_framework import serializers

from apps.workspaces.serializers import (
    JobRoleSerializer,
    TeamMemberJobRoleUpdateSerializer,
    TeamMemberSerializer,
    WorkspaceSerializer,
)


class WorkspaceSerializerValidationTests(SimpleTestCase):
    def test_validate_organization_rejects_none(self):
        serializer = WorkspaceSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_organization(None)

        self.assertIn("This field is required.", str(ctx.exception))

    @patch("apps.workspaces.serializers.api.user_can_access_organization")
    def test_validate_organization_rejects_inaccessible_organization(
        self,
        user_can_access_organization,
    ):
        user_can_access_organization.return_value = False
        user = SimpleNamespace(is_authenticated=True)
        request = SimpleNamespace(user=user)
        organization = SimpleNamespace(id=1)

        serializer = WorkspaceSerializer(context={"request": request})

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_organization(organization)

        self.assertIn("Invalid organization", str(ctx.exception))
        user_can_access_organization.assert_called_once_with(user, organization)

    @patch("apps.workspaces.serializers.api.user_can_access_organization")
    def test_validate_organization_accepts_accessible_organization(
        self,
        user_can_access_organization,
    ):
        user_can_access_organization.return_value = True
        user = SimpleNamespace(is_authenticated=True)
        request = SimpleNamespace(user=user)
        organization = SimpleNamespace(id=1)

        serializer = WorkspaceSerializer(context={"request": request})

        result = serializer.validate_organization(organization)

        self.assertIs(result, organization)

    def test_validate_organization_allows_when_no_request_context(self):
        organization = SimpleNamespace(id=1)
        serializer = WorkspaceSerializer()

        result = serializer.validate_organization(organization)

        self.assertIs(result, organization)

    def test_validate_name_rejects_blank_value(self):
        serializer = WorkspaceSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_name("   ")

        self.assertIn("This field may not be blank.", str(ctx.exception))

    def test_validate_name_strips_value(self):
        serializer = WorkspaceSerializer()

        self.assertEqual(serializer.validate_name("  Product  "), "Product")


class WorkspaceSerializerDuplicateTests(SimpleTestCase):
    @patch("apps.workspaces.serializers.api.Workspace.objects.filter")
    def test_validate_rejects_duplicate_workspace_name_on_create(
        self,
        workspace_filter,
    ):
        qs = MagicMock()
        qs.exists.return_value = True
        workspace_filter.return_value = qs

        organization = SimpleNamespace(id=1)
        serializer = WorkspaceSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate(
                {
                    "name": "Engineering",
                    "organization": organization,
                }
            )

        self.assertIn("workspace with this name already exists", str(ctx.exception))
        workspace_filter.assert_called_once_with(
            organization=organization,
            name__iexact="Engineering",
        )

    @patch("apps.workspaces.serializers.api.Workspace.objects.filter")
    def test_validate_allows_unique_workspace_name_on_create(
        self,
        workspace_filter,
    ):
        qs = MagicMock()
        qs.exists.return_value = False
        workspace_filter.return_value = qs

        organization = SimpleNamespace(id=1)
        attrs = {
            "name": "Engineering",
            "organization": organization,
        }
        serializer = WorkspaceSerializer()

        result = serializer.validate(attrs)

        self.assertIs(result, attrs)

    @patch("apps.workspaces.serializers.api.Workspace.objects.filter")
    def test_validate_excludes_current_instance_on_update(
        self,
        workspace_filter,
    ):
        qs = MagicMock()
        qs.exclude.return_value = qs
        qs.exists.return_value = False
        workspace_filter.return_value = qs

        organization = SimpleNamespace(id=1)
        instance = SimpleNamespace(
            pk=10,
            name="Engineering",
            organization=organization,
        )
        serializer = WorkspaceSerializer(instance=instance)

        result = serializer.validate({})

        self.assertEqual(result, {})
        qs.exclude.assert_called_once_with(pk=10)

    @patch("apps.workspaces.serializers.api.Workspace.objects.filter")
    def test_validate_rejects_duplicate_workspace_name_on_update(
        self,
        workspace_filter,
    ):
        qs = MagicMock()
        qs.exclude.return_value = qs
        qs.exists.return_value = True
        workspace_filter.return_value = qs

        organization = SimpleNamespace(id=1)
        instance = SimpleNamespace(
            pk=10,
            name="Old Name",
            organization=organization,
        )
        serializer = WorkspaceSerializer(instance=instance)

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate({"name": "Engineering"})

        self.assertIn("workspace with this name already exists", str(ctx.exception))
        qs.exclude.assert_called_once_with(pk=10)


class WorkspaceSerializerCreateUpdateTests(SimpleTestCase):
    @patch("apps.workspaces.serializers.api.TeamMember.objects.get_or_create")
    @patch("rest_framework.serializers.ModelSerializer.create")
    def test_create_adds_request_user_as_workspace_admin(
        self,
        model_serializer_create,
        get_or_create,
    ):
        user = SimpleNamespace(is_authenticated=True)
        request = SimpleNamespace(user=user)
        workspace = SimpleNamespace(id=1)
        model_serializer_create.return_value = workspace

        serializer = WorkspaceSerializer(context={"request": request})
        result = serializer.create({"name": "Engineering"})

        self.assertIs(result, workspace)
        get_or_create.assert_called_once()
        kwargs = get_or_create.call_args.kwargs
        self.assertIs(kwargs["workspace"], workspace)
        self.assertIs(kwargs["user"], user)
        self.assertEqual(kwargs["defaults"]["role"], "workspace_admin")

    @patch("apps.workspaces.serializers.api.TeamMember.objects.get_or_create")
    @patch("rest_framework.serializers.ModelSerializer.create")
    def test_create_does_not_add_team_member_without_request(
        self,
        model_serializer_create,
        get_or_create,
    ):
        workspace = SimpleNamespace(id=1)
        model_serializer_create.return_value = workspace

        serializer = WorkspaceSerializer()
        result = serializer.create({"name": "Engineering"})

        self.assertIs(result, workspace)
        get_or_create.assert_not_called()

    @patch("rest_framework.serializers.ModelSerializer.create")
    def test_create_converts_integrity_error_to_validation_error(
        self,
        model_serializer_create,
    ):
        model_serializer_create.side_effect = IntegrityError("duplicate")

        serializer = WorkspaceSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.create({"name": "Engineering"})

        self.assertIn("workspace with this name already exists", str(ctx.exception))

    @patch("rest_framework.serializers.ModelSerializer.update")
    def test_update_returns_updated_instance(
        self,
        model_serializer_update,
    ):
        instance = SimpleNamespace(id=1)
        updated = SimpleNamespace(id=1, name="Updated")
        model_serializer_update.return_value = updated

        serializer = WorkspaceSerializer()
        result = serializer.update(instance, {"name": "Updated"})

        self.assertIs(result, updated)

    @patch("rest_framework.serializers.ModelSerializer.update")
    def test_update_converts_integrity_error_to_validation_error(
        self,
        model_serializer_update,
    ):
        model_serializer_update.side_effect = IntegrityError("duplicate")

        serializer = WorkspaceSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.update(SimpleNamespace(id=1), {"name": "Engineering"})

        self.assertIn("workspace with this name already exists", str(ctx.exception))


class JobRoleSerializerTests(SimpleTestCase):
    def test_job_role_serializer_exposes_expected_fields_as_read_only(self):
        serializer = JobRoleSerializer()

        self.assertEqual(
            serializer.Meta.fields,
            (
                "id",
                "code",
                "name",
                "description",
                "task_categories",
                "is_active",
            ),
        )
        self.assertEqual(serializer.Meta.read_only_fields, serializer.Meta.fields)


class TeamMemberSerializerTests(SimpleTestCase):
    def test_get_task_categories_returns_job_role_categories(self):
        serializer = TeamMemberSerializer()
        obj = SimpleNamespace(
            job_role_id=1,
            job_role=SimpleNamespace(task_categories=["backend", "frontend"]),
        )

        result = serializer.get_task_categories(obj)

        self.assertEqual(result, ["backend", "frontend"])

    def test_get_task_categories_returns_empty_list_without_job_role_id(self):
        serializer = TeamMemberSerializer()
        obj = SimpleNamespace(job_role_id=None, job_role=None)

        result = serializer.get_task_categories(obj)

        self.assertEqual(result, [])

    def test_get_task_categories_returns_empty_list_without_categories(self):
        serializer = TeamMemberSerializer()
        obj = SimpleNamespace(
            job_role_id=1,
            job_role=SimpleNamespace(task_categories=None),
        )

        result = serializer.get_task_categories(obj)

        self.assertEqual(result, [])


class TeamMemberJobRoleUpdateSerializerTests(SimpleTestCase):
    def test_validate_job_role_id_allows_none(self):
        serializer = TeamMemberJobRoleUpdateSerializer()

        self.assertIsNone(serializer.validate_job_role_id(None))

    @patch("apps.workspaces.serializers.api.JobRole.objects.filter")
    def test_validate_job_role_id_accepts_active_job_role(self, job_role_filter):
        qs = MagicMock()
        qs.exists.return_value = True
        job_role_filter.return_value = qs

        serializer = TeamMemberJobRoleUpdateSerializer()

        self.assertEqual(serializer.validate_job_role_id(123), 123)
        job_role_filter.assert_called_once_with(pk=123, is_active=True)

    @patch("apps.workspaces.serializers.api.JobRole.objects.filter")
    def test_validate_job_role_id_rejects_missing_or_inactive_job_role(
        self,
        job_role_filter,
    ):
        qs = MagicMock()
        qs.exists.return_value = False
        job_role_filter.return_value = qs

        serializer = TeamMemberJobRoleUpdateSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_job_role_id(123)

        self.assertIn("Job role not found.", str(ctx.exception))
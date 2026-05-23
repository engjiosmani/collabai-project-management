from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import serializers

from apps.organizations.models import Organization, OrganizationMember
from apps.user_profiles.models import Profile
from apps.user_profiles.serializers import (
    ChangePasswordSerializer,
    MembershipSerializer,
    ProfileDetailSerializer,
    ProfileSerializer,
    UserMeSerializer,
    UserSerializer,
)
from apps.workspaces.models import TeamMember, Workspace

User = get_user_model()


class UserProfileSerializerTests(TestCase):
    def test_user_serializer_returns_none_when_profile_missing(self):
        user = User.objects.create_user(
            username="missing_profile",
            email="missing@example.com",
            password="password123",
        )
        Profile.objects.filter(user=user).delete()

        data = UserSerializer(user).data

        self.assertIsNone(data["profile"])

    def test_user_serializer_returns_profile_data_when_profile_exists(self):
        organization = Organization.objects.create(name="Org")
        user = User.objects.create_user(
            username="with_profile",
            email="with@example.com",
            password="password123",
        )
        Profile.objects.create(
            user=user,
            organization=organization,
            bio="Bio text",
            phone_number="12345",
        )

        data = UserSerializer(user).data

        self.assertIsNotNone(data["profile"])
        self.assertEqual(data["profile"]["bio"], "Bio text")
        self.assertEqual(data["profile"]["phone_number"], "12345")
        self.assertEqual(data["profile"]["organization_name"], "Org")

    def test_profile_serializer_includes_organization_name(self):
        organization = Organization.objects.create(name="Org Name")
        user = User.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="password123",
        )
        profile = Profile.objects.create(
            user=user,
            organization=organization,
            bio="Hello",
            phone_number="555",
        )

        data = ProfileSerializer(profile).data

        self.assertEqual(data["organization_name"], "Org Name")
        self.assertEqual(data["bio"], "Hello")
        self.assertEqual(data["phone_number"], "555")


class UserMeSerializerTests(TestCase):
    def test_validate_organization_accepts_accessible_organization(self):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="password123",
        )
        organization = Organization.objects.create(name="Org")
        OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role="member",
        )

        serializer = UserMeSerializer(instance=user)

        self.assertEqual(serializer.validate_organization(organization), organization)

    def test_validate_organization_allows_none(self):
        user = User.objects.create_user(
            username="none_org",
            email="none@example.com",
            password="password123",
        )

        serializer = UserMeSerializer(instance=user)

        self.assertIsNone(serializer.validate_organization(None))

    @patch("apps.user_profiles.serializers.api.user_can_access_organization")
    def test_validate_organization_rejects_inaccessible_organization(
        self,
        user_can_access_organization,
    ):
        user_can_access_organization.return_value = False
        user = User.objects.create_user(
            username="blocked",
            email="blocked@example.com",
            password="password123",
        )
        organization = Organization.objects.create(name="Blocked Org")

        serializer = UserMeSerializer(instance=user)

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_organization(organization)

        self.assertIn("Invalid organization", str(ctx.exception))

    def test_update_updates_user_fields_and_creates_profile(self):
        user = User.objects.create_user(
            username="update_me",
            email="old@example.com",
            password="password123",
            first_name="Old",
            last_name="Name",
        )
        organization = Organization.objects.create(name="Org")
        OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role="member",
        )

        serializer = UserMeSerializer(instance=user)
        result = serializer.update(
            user,
            {
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Person",
                "bio": "New bio",
                "phone_number": "555-123",
                "organization": organization,
            },
        )

        result.refresh_from_db()
        profile = result.profile

        self.assertEqual(result.email, "new@example.com")
        self.assertEqual(result.first_name, "New")
        self.assertEqual(result.last_name, "Person")
        self.assertEqual(profile.bio, "New bio")
        self.assertEqual(profile.phone_number, "555-123")
        self.assertEqual(profile.organization, organization)

    def test_update_only_updates_profile_fields_when_present(self):
        user = User.objects.create_user(
            username="partial_update",
            email="partial@example.com",
            password="password123",
        )
        profile = Profile.objects.create(user=user, bio="Old bio")

        serializer = UserMeSerializer(instance=user)
        serializer.update(user, {"bio": "Updated bio"})

        profile.refresh_from_db()
        user.refresh_from_db()

        self.assertEqual(profile.bio, "Updated bio")
        self.assertEqual(user.email, "partial@example.com")


class ProfileDetailSerializerTests(TestCase):
    def test_to_representation_without_profile_returns_empty_profile_fields(self):
        user = User.objects.create_user(
            username="no_profile_detail",
            email="detail@example.com",
            password="password123",
        )
        Profile.objects.filter(user=user).delete()

        data = ProfileDetailSerializer(user).data

        self.assertEqual(data["bio"], "")
        self.assertEqual(data["phone_number"], "")
        self.assertIsNone(data["avatar"])

    def test_to_representation_with_profile_without_avatar(self):
        user = User.objects.create_user(
            username="with_profile_detail",
            email="withdetail@example.com",
            password="password123",
        )
        Profile.objects.create(
            user=user,
            bio="Detail bio",
            phone_number="123",
        )

        data = ProfileDetailSerializer(user).data

        self.assertEqual(data["bio"], "Detail bio")
        self.assertEqual(data["phone_number"], "123")
        self.assertIsNone(data["avatar"])

    def test_to_representation_with_avatar_uses_request_absolute_uri(self):
        user = User.objects.create_user(
            username="avatar_user",
            email="avatar@example.com",
            password="password123",
        )
        profile = Profile.objects.create(user=user)
        profile.avatar = SimpleNamespace(
            url="/media/avatar.png",
            __bool__=lambda self: True,
        )

        request = MagicMock()
        request.build_absolute_uri.return_value = "http://testserver/media/avatar.png"

        serializer = ProfileDetailSerializer(
            user,
            context={"request": request},
        )

        data = serializer.to_representation(user)

        self.assertEqual(data["avatar"], "http://testserver/media/avatar.png")
        request.build_absolute_uri.assert_called_once_with("/media/avatar.png")

    def test_update_updates_user_and_profile_fields(self):
        user = User.objects.create_user(
            username="detail_update",
            email="old@example.com",
            password="password123",
            first_name="Old",
        )

        serializer = ProfileDetailSerializer(instance=user)
        result = serializer.update(
            user,
            {
                "email": "new@example.com",
                "first_name": "New",
                "bio": "Bio",
                "phone_number": "999",
            },
        )

        result.refresh_from_db()
        profile = result.profile

        self.assertEqual(result.email, "new@example.com")
        self.assertEqual(result.first_name, "New")
        self.assertEqual(profile.bio, "Bio")
        self.assertEqual(profile.phone_number, "999")

    def test_update_user_only_does_not_create_profile_when_no_profile_fields(self):
        user = User.objects.create_user(
            username="user_only",
            email="old@example.com",
            password="password123",
        )
        Profile.objects.filter(user=user).delete()

        serializer = ProfileDetailSerializer(instance=user)
        serializer.update(user, {"email": "changed@example.com"})

        user.refresh_from_db()

        self.assertEqual(user.email, "changed@example.com")
        self.assertFalse(Profile.objects.filter(user=user).exists())


class ChangePasswordSerializerTests(TestCase):
    def test_validate_old_password_accepts_correct_password(self):
        user = User.objects.create_user(
            username="password_user",
            email="password@example.com",
            password="old-password",
        )
        request = SimpleNamespace(user=user)
        serializer = ChangePasswordSerializer(context={"request": request})

        self.assertEqual(
            serializer.validate_old_password("old-password"),
            "old-password",
        )

    def test_validate_old_password_rejects_wrong_password(self):
        user = User.objects.create_user(
            username="wrong_password_user",
            email="wrong@example.com",
            password="old-password",
        )
        request = SimpleNamespace(user=user)
        serializer = ChangePasswordSerializer(context={"request": request})

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate_old_password("wrong-password")

        self.assertIn("Old password is incorrect.", str(ctx.exception))

    def test_validate_accepts_matching_passwords(self):
        serializer = ChangePasswordSerializer()

        data = {
            "old_password": "old-password",
            "new_password": "new-password",
            "confirm_password": "new-password",
        }

        self.assertEqual(serializer.validate(data), data)

    def test_validate_rejects_mismatched_passwords(self):
        serializer = ChangePasswordSerializer()

        with self.assertRaises(serializers.ValidationError) as ctx:
            serializer.validate(
                {
                    "old_password": "old-password",
                    "new_password": "new-password",
                    "confirm_password": "different-password",
                }
            )

        self.assertIn("Passwords do not match.", str(ctx.exception))


class MembershipSerializerTests(TestCase):
    def test_get_organization_returns_id_and_name(self):
        user = User.objects.create_user(
            username="org_member",
            email="orgmember@example.com",
            password="password123",
        )
        organization = Organization.objects.create(name="Org")
        membership = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role="admin",
        )

        serializer = MembershipSerializer()

        self.assertEqual(
            serializer.get_organization(membership),
            {
                "id": organization.id,
                "name": "Org",
            },
        )

    def test_get_workspaces_returns_user_workspaces_for_organization(self):
        user = User.objects.create_user(
            username="workspace_member",
            email="workspace@example.com",
            password="password123",
        )
        organization = Organization.objects.create(name="Org")
        other_org = Organization.objects.create(name="Other Org")

        membership = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role="member",
        )

        workspace = Workspace.objects.create(
            organization=organization,
            name="Main Workspace",
        )
        other_workspace = Workspace.objects.create(
            organization=other_org,
            name="Other Workspace",
        )

        TeamMember.objects.create(
            workspace=workspace,
            user=user,
            role="member",
        )
        TeamMember.objects.create(
            workspace=other_workspace,
            user=user,
            role="member",
        )

        serializer = MembershipSerializer()
        data = serializer.get_workspaces(membership)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], workspace.id)
        self.assertEqual(data[0]["name"], "Main Workspace")
        self.assertEqual(data[0]["role"], "member")
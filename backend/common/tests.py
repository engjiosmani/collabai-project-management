from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from rest_framework.test import APIRequestFactory

from common.permissions import (
    IsOwner,
    HasRole,
    HasAnyRole,
    user_matches_any_required_role,
)
from common.tenant_access import (
    organizations_queryset_for_user,
    resolve_organization,
    user_can_access_organization,
)

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority

User = get_user_model()


class DummyObj:
    def __init__(self, user=None):
        self.user = user


class DummyView:
    required_role = "Admin"
    required_roles = ("Admin", "Manager")


class CommonTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            email="user@test.com",
            username="user@test.com",
            password="Password123!",
        )

        self.other = User.objects.create_user(
            email="other@test.com",
            username="other@test.com",
            password="Password123!",
        )

    def test_is_owner_true(self):
        request = self.factory.get("/")
        request.user = self.user
        obj = DummyObj(user=self.user)
        self.assertTrue(IsOwner().has_object_permission(request, None, obj))

    def test_is_owner_false(self):
        request = self.factory.get("/")
        request.user = self.user
        obj = DummyObj(user=self.other)
        self.assertFalse(IsOwner().has_object_permission(request, None, obj))

    def test_has_role_without_required_role(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(HasRole().has_permission(request, None))

    def test_has_any_role_false(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertFalse(HasAnyRole().has_permission(request, DummyView()))

    def test_anonymous_has_no_organizations(self):
        qs = organizations_queryset_for_user(AnonymousUser())
        self.assertEqual(qs.count(), 0)

    def test_user_cannot_access_none_organization(self):
        self.assertFalse(user_can_access_organization(self.user, None))

    def test_user_matches_group_role(self):
        group = Group.objects.create(name="Manager")
        self.user.groups.add(group)
        self.assertTrue(user_matches_any_required_role(self.user, ("Manager",)))

    def test_user_does_not_match_required_role(self):
        self.assertFalse(user_matches_any_required_role(self.user, ("Admin",)))

    def test_user_matches_no_required_roles_returns_true(self):
        self.assertTrue(user_matches_any_required_role(self.user, ()))

    def test_organizations_queryset_for_member(self):
        org = Organization.objects.create(name="Access Org")
        OrganizationMember.objects.create(organization=org, user=self.user)

        qs = organizations_queryset_for_user(self.user)
        self.assertIn(org, qs)

    def test_user_can_access_organization_as_member(self):
        org = Organization.objects.create(name="Can Access Org")
        OrganizationMember.objects.create(organization=org, user=self.user)
        self.assertTrue(user_can_access_organization(self.user, org))

    def test_user_cannot_access_organization_if_not_member(self):
        org = Organization.objects.create(name="Cannot Access Org")
        self.assertFalse(user_can_access_organization(self.user, org))

    def test_resolve_organization_from_project(self):
        org = Organization.objects.create(name="Resolve Org")
        project = Project.objects.create(name="Resolve Project", organization=org)
        self.assertEqual(resolve_organization(project), org)

    def test_resolve_organization_from_task(self):
        org = Organization.objects.create(name="Resolve Task Org")
        project = Project.objects.create(name="Resolve Task Project", organization=org)

        status, _ = TaskStatus.objects.get_or_create(name="To Do")
        priority, _ = TaskPriority.objects.get_or_create(
            level=2,
            defaults={"name": "Medium"},
        )
        task = Task.objects.create(
            project=project,
            title="Resolve Task",
            status=status,
            priority=priority,
        )
        self.assertEqual(resolve_organization(task), org)

    def test_resolve_organization_returns_none_for_unknown_object(self):
        self.assertIsNone(resolve_organization(object()))

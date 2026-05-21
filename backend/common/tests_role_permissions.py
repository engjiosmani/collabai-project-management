from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import TeamMember, Workspace
from common.role_permissions import IsOrgAdmin, IsWorkspaceAdmin, IsManagerOrAbove, IsMember

User = get_user_model()


def _make_request(user):
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user
    return request


class IsOrgAdminTest(TestCase):
    def setUp(self):
        self.org_admin = User.objects.create_user(username='orgadmin@test.com', password='x')
        self.plain_member = User.objects.create_user(username='orgmember@test.com', password='x')
        self.outsider = User.objects.create_user(username='orgoutsider@test.com', password='x')
        self.org = Organization.objects.create(name='IsOrgAdmin Org')
        OrganizationMember.objects.create(
            organization=self.org, user=self.org_admin, role=OrganizationMember.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            organization=self.org, user=self.plain_member, role=OrganizationMember.MEMBER
        )
        self.perm = IsOrgAdmin()

    def test_org_admin_passes(self):
        self.assertTrue(self.perm.has_object_permission(_make_request(self.org_admin), None, self.org))

    def test_plain_member_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.plain_member), None, self.org))

    def test_outsider_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.outsider), None, self.org))

    def test_superuser_passes(self):
        su = User.objects.create_user(username='su@test.com', password='x', is_superuser=True)
        self.assertTrue(self.perm.has_object_permission(_make_request(su), None, self.org))


class IsWorkspaceAdminTest(TestCase):
    def setUp(self):
        self.ws_admin = User.objects.create_user(username='wsadmin@test.com', password='x')
        self.manager = User.objects.create_user(username='wsmgr@test.com', password='x')
        self.plain_member = User.objects.create_user(username='wsmem@test.com', password='x')
        self.org = Organization.objects.create(name='IsWorkspaceAdmin Org')
        self.ws = Workspace.objects.create(name='Test WS', organization=self.org)
        TeamMember.objects.create(workspace=self.ws, user=self.ws_admin, role=TeamMember.WORKSPACE_ADMIN)
        TeamMember.objects.create(workspace=self.ws, user=self.manager, role=TeamMember.MANAGER)
        TeamMember.objects.create(workspace=self.ws, user=self.plain_member, role=TeamMember.MEMBER)
        self.perm = IsWorkspaceAdmin()

    def test_workspace_admin_passes(self):
        self.assertTrue(self.perm.has_object_permission(_make_request(self.ws_admin), None, self.ws))

    def test_manager_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.manager), None, self.ws))

    def test_plain_member_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.plain_member), None, self.ws))


class IsManagerOrAboveTest(TestCase):
    def setUp(self):
        self.ws_admin = User.objects.create_user(username='mab_wsadmin@test.com', password='x')
        self.manager = User.objects.create_user(username='mab_mgr@test.com', password='x')
        self.plain_member = User.objects.create_user(username='mab_mem@test.com', password='x')
        self.org = Organization.objects.create(name='IsManagerOrAbove Org')
        self.ws = Workspace.objects.create(name='Mgr WS', organization=self.org)
        TeamMember.objects.create(workspace=self.ws, user=self.ws_admin, role=TeamMember.WORKSPACE_ADMIN)
        TeamMember.objects.create(workspace=self.ws, user=self.manager, role=TeamMember.MANAGER)
        TeamMember.objects.create(workspace=self.ws, user=self.plain_member, role=TeamMember.MEMBER)
        self.perm = IsManagerOrAbove()

    def test_workspace_admin_passes(self):
        self.assertTrue(self.perm.has_object_permission(_make_request(self.ws_admin), None, self.ws))

    def test_manager_passes(self):
        self.assertTrue(self.perm.has_object_permission(_make_request(self.manager), None, self.ws))

    def test_plain_member_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.plain_member), None, self.ws))


class IsMemberTest(TestCase):
    def setUp(self):
        self.member_user = User.objects.create_user(username='member_p@test.com', password='x')
        self.outsider = User.objects.create_user(username='outsider_p@test.com', password='x')
        self.org = Organization.objects.create(name='IsMember Org')
        OrganizationMember.objects.create(
            organization=self.org, user=self.member_user, role=OrganizationMember.MEMBER
        )
        self.perm = IsMember()

    def test_org_member_passes(self):
        self.assertTrue(self.perm.has_object_permission(_make_request(self.member_user), None, self.org))

    def test_outsider_denied(self):
        self.assertFalse(self.perm.has_object_permission(_make_request(self.outsider), None, self.org))


class BackwardCompatAliasTest(TestCase):
    def test_is_admin_alias(self):
        from common.role_permissions import IsAdmin
        self.assertIs(IsAdmin, IsOrgAdmin)

    def test_is_manager_or_admin_alias(self):
        from common.role_permissions import IsManagerOrAdmin
        self.assertIs(IsManagerOrAdmin, IsManagerOrAbove)
import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.workspaces.models import TeamMember, Workspace
from .models import Organization, OrganizationInvite, OrganizationMember
User = get_user_model()
def _jwt(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}
def _make_user(username, email=None):
    email = email or f'{username}@example.com'
    return User.objects.create_user(username=username, email=email, password='x')
# ── Model tests ───────────────────────────────────────────────────────────────
class OrganizationModelTest(TestCase):
    def test_create_organization(self):
        org = Organization.objects.create(name='Test Org')
        self.assertEqual(org.name, 'Test Org')
    def test_str(self):
        org = Organization.objects.create(name='MyOrg')
        self.assertEqual(str(org), 'MyOrg')
class OrganizationMemberRoleChoicesTest(TestCase):
    def test_role_choices_count(self):
        self.assertEqual(len(OrganizationMember.ROLE_CHOICES), 2)
    def test_org_admin_constant(self):
        self.assertEqual(OrganizationMember.ORG_ADMIN, 'org_admin')
    def test_member_constant(self):
        self.assertEqual(OrganizationMember.MEMBER, 'member')
    def test_role_choice_values(self):
        values = [v for v, _ in OrganizationMember.ROLE_CHOICES]
        self.assertIn('org_admin', values)
        self.assertIn('member', values)
        self.assertNotIn('owner', values)
        self.assertNotIn('admin', values)
class OrganizationInviteModelTest(TestCase):
    def test_invite_has_four_role_choices(self):
        values = [v for v, _ in OrganizationInvite.ROLE_CHOICES]
        self.assertIn('org_admin', values)
        self.assertIn('workspace_admin', values)
        self.assertIn('manager', values)
        self.assertIn('member', values)
    def test_invite_default_not_accepted(self):
        org = Organization.objects.create(name='Org')
        invite = OrganizationInvite.objects.create(
            organization=org,
            email='x@x.com',
            role=OrganizationInvite.MEMBER,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertFalse(invite.is_accepted)
# ── Base setup ────────────────────────────────────────────────────────────────
class BaseOrgAPI(APITestCase):
    def setUp(self):
        self.creator = _make_user('creator_user', 'creator@example.com')
        self.admin = _make_user('admin_user', 'admin@example.com')
        self.member = _make_user('member_user', 'member@example.com')
        self.outsider = _make_user('outsider_user', 'outsider@example.com')
        self.org = Organization.objects.create(name='Alpha Corp')
        OrganizationMember.objects.create(
            organization=self.org, user=self.creator, role=OrganizationMember.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            organization=self.org, user=self.admin, role=OrganizationMember.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            organization=self.org, user=self.member, role=OrganizationMember.MEMBER
        )
        self.workspace = Workspace.objects.create(name='Main WS', organization=self.org)
# ── Org CRUD ──────────────────────────────────────────────────────────────────
class OrganizationCRUDTest(BaseOrgAPI):
    def test_unauthenticated_returns_401(self):
        res = self.client.get('/api/v1/organizations/')
        self.assertEqual(res.status_code, 401)
    def test_list_returns_only_member_orgs(self):
        Organization.objects.create(name='Other Corp')
        res = self.client.get('/api/v1/organizations/', **_jwt(self.admin))
        self.assertEqual(res.status_code, 200)
        names = [o['name'] for o in res.data.get('results', res.data)]
        self.assertIn('Alpha Corp', names)
        self.assertNotIn('Other Corp', names)

    def test_list_includes_current_user_workspace_roles(self):
        TeamMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=TeamMember.MANAGER,
        )
        res = self.client.get('/api/v1/organizations/', **_jwt(self.member))
        self.assertEqual(res.status_code, 200)
        org_data = res.data.get('results', res.data)[0]
        self.assertEqual(org_data['my_role'], OrganizationMember.MEMBER)
        self.assertEqual(
            org_data['my_workspace_roles'],
            {str(self.workspace.pk): TeamMember.MANAGER},
        )

    def test_create_org_auto_assigns_org_admin(self):
        res = self.client.post(
            '/api/v1/organizations/',
            {'name': 'New Org'},
            format='json',
            **_jwt(self.creator),
        )
        self.assertEqual(res.status_code, 201, res.data)
        org = Organization.objects.get(pk=res.data['id'])
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=org,
                user=self.creator,
                role=OrganizationMember.ORG_ADMIN,
            ).exists()
        )
    def test_member_cannot_update_org(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/',
            {'description': 'hacked'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_admin_can_update_org(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/',
            {'description': 'updated'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['description'], 'updated')
    def test_outsider_cannot_retrieve_org(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.outsider),
        )
        self.assertEqual(res.status_code, 404)
    def test_member_cannot_delete_org(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_org_admin_can_delete_org(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Organization.objects.filter(pk=self.org.pk).exists())
    def test_creator_org_admin_can_delete_org(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.creator),
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Organization.objects.filter(pk=self.org.pk).exists())
    def test_deleted_org_not_in_list(self):
        self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.creator),
        )
        res = self.client.get(
            '/api/v1/organizations/',
            **_jwt(self.creator),
        )
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        ids = [o['id'] for o in results]
        self.assertNotIn(self.org.pk, ids)
    def test_deleted_org_returns_404(self):
        self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.creator),
        )
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/',
            **_jwt(self.creator),
        )
        self.assertEqual(res.status_code, 404)
# ── Members ───────────────────────────────────────────────────────────────────
class OrgMembersTest(BaseOrgAPI):
    def test_list_members(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/members/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 3)
    def test_admin_can_update_member_role(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/members/{self.member.pk}/',
            {'role': 'org_admin'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=self.org, user=self.member, role='org_admin'
            ).exists()
        )
    def test_member_cannot_update_other_member_role(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/members/{self.admin.pk}/',
            {'role': 'member'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_admin_can_remove_member(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/members/{self.member.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization=self.org, user=self.member
            ).exists()
        )
    def test_admin_cannot_remove_self(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/members/{self.admin.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 400)
    def test_remove_member_cascades_workspace_memberships(self):
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.MEMBER
        )
        self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/members/{self.member.pk}/',
            **_jwt(self.admin),
        )
        self.assertFalse(
            TeamMember.objects.filter(
                workspace=self.workspace, user=self.member
            ).exists()
        )
# ── Invitations ───────────────────────────────────────────────────────────────
class OrgInviteTest(BaseOrgAPI):
    def test_admin_can_send_invite(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'new@example.com', 'role': 'member'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIn('token', res.data)
        self.assertFalse(res.data['is_accepted'])

    def test_invite_existing_user_creates_unread_notification(self):
        invitee = _make_user('invitee-notify', 'notify-invite@example.com')

        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': invitee.email, 'role': 'member'},
            format='json',
            **_jwt(self.admin),
        )

        self.assertEqual(res.status_code, 201, res.data)

        from apps.notifications.models import Notification

        notification = Notification.objects.filter(
            user=invitee,
            title='Organization invitation',
            is_read=False,
        ).first()

        self.assertIsNotNone(notification)
        self.assertIsNone(notification.organization)
        self.assertIn(self.org.name, notification.message)

    def test_invite_token_is_valid_uuid(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'uuid@example.com'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 201)
        try:
            uuid.UUID(res.data['token'])
        except ValueError:
            self.fail('token is not a valid UUID')
    def test_invite_expires_in_7_days(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'expiry@example.com'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 201)
        invite = OrganizationInvite.objects.get(token=res.data['token'])
        delta = invite.expires_at - timezone.now()
        self.assertGreater(delta.days, 5)
    def test_member_cannot_send_invite(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'blocked@example.com'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_reinvite_updates_token_not_duplicates(self):
        self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'reinvite@example.com'},
            format='json',
            **_jwt(self.admin),
        )
        first_token = OrganizationInvite.objects.get(
            organization=self.org, email='reinvite@example.com'
        ).token
        self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'reinvite@example.com'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(
            OrganizationInvite.objects.filter(
                organization=self.org, email='reinvite@example.com'
            ).count(),
            1,
        )
        second_token = OrganizationInvite.objects.get(
            organization=self.org, email='reinvite@example.com'
        ).token
        self.assertNotEqual(first_token, second_token)
    def test_invite_invalid_workspace_returns_400(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/invite/',
            {'email': 'ws@example.com', 'workspace_id': 99999},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 400)
# ── Accept invite.txt ─────────────────────────────────────────────────────────────
class AcceptInviteTest(BaseOrgAPI):
    def _make_invite(self, email, role='member', expired=False):
        return OrganizationInvite.objects.create(
            organization=self.org,
            email=email,
            role=role,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=-1 if expired else 7),
        )
    def test_accept_valid_invite(self):
        invitee = _make_user('invitee', 'acceptme@example.com')
        invite = self._make_invite('acceptme@example.com')
        res = self.client.post(
            f'/api/v1/invites/{invite.token}/accept/',
            **_jwt(invitee),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=self.org, user=invitee
            ).exists()
        )
        invite.refresh_from_db()
        self.assertTrue(invite.is_accepted)
    def test_expired_invite_returns_400(self):
        invitee = _make_user('expireduser', 'exp@example.com')
        invite = self._make_invite('exp@example.com', expired=True)
        res = self.client.post(
            f'/api/v1/invites/{invite.token}/accept/',
            **_jwt(invitee),
        )
        self.assertEqual(res.status_code, 400)
    def test_already_accepted_invite_returns_400(self):
        invitee = _make_user('doubleuser', 'double@example.com')
        invite = self._make_invite('double@example.com')
        invite.is_accepted = True
        invite.save()
        res = self.client.post(
            f'/api/v1/invites/{invite.token}/accept/',
            **_jwt(invitee),
        )
        self.assertEqual(res.status_code, 400)
    def test_nonexistent_token_returns_404(self):
        invitee = _make_user('ghost', 'ghost@example.com')
        res = self.client.post(
            '/api/v1/invites/this-token-does-not-exist/accept/',
            **_jwt(invitee),
        )
        self.assertEqual(res.status_code, 404)
    def test_invite_accept_requires_matching_email(self):
        wrong_user = _make_user('wronginvitee', 'wrong@example.com')
        invite = self._make_invite('right@example.com')
        res = self.client.post(
            f'/api/v1/invites/{invite.token}/accept/',
            **_jwt(wrong_user),
        )
        self.assertEqual(res.status_code, 403)
        invite.refresh_from_db()
        self.assertFalse(invite.is_accepted)
    def test_unauthenticated_returns_401(self):
        invite = self._make_invite('anon@example.com')
        res = self.client.post(f'/api/v1/invites/{invite.token}/accept/')
        self.assertEqual(res.status_code, 401)
    def test_accept_with_workspace_creates_team_member(self):
        invitee = _make_user('wsinvitee', 'wsinvitee@example.com')
        invite = OrganizationInvite.objects.create(
            organization=self.org,
            email='wsinvitee@example.com',
            role=OrganizationInvite.WORKSPACE_ADMIN,
            workspace=self.workspace,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7),
        )
        res = self.client.post(
            f'/api/v1/invites/{invite.token}/accept/',
            **_jwt(invitee),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(
            TeamMember.objects.filter(
                workspace=self.workspace,
                user=invitee,
                role=TeamMember.WORKSPACE_ADMIN,
            ).exists()
        )
# ── Workspaces nested under org ───────────────────────────────────────────────
class OrgWorkspacesTest(BaseOrgAPI):
    def test_list_workspaces(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        names = [w['name'] for w in res.data]
        self.assertIn('Main WS', names)
    def test_outsider_cannot_list_workspaces(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/',
            **_jwt(self.outsider),
        )
        self.assertEqual(res.status_code, 404)
    def test_admin_can_create_workspace(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/',
            {'name': 'New Workspace', 'is_active': True},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(
            Workspace.objects.filter(name='New Workspace', organization=self.org).exists()
        )
    def test_member_cannot_create_workspace(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/',
            {'name': 'Blocked WS'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_retrieve_workspace(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'Main WS')
    def test_admin_can_update_workspace(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/',
            {'name': 'Renamed WS'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'Renamed WS')
    def test_member_cannot_update_workspace(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/',
            {'name': 'Hacked'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_workspace_admin_can_update_workspace(self):
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.WORKSPACE_ADMIN
        )
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/',
            {'name': 'WS Admin Update'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 200)
    def test_admin_can_delete_workspace(self):
        ws = Workspace.objects.create(name='Delete Me', organization=self.org)
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{ws.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 204)
        ws.refresh_from_db()
        self.assertFalse(ws.is_active)
    def test_member_cannot_delete_workspace(self):
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_creator_org_admin_can_delete_workspace(self):
        ws = Workspace.objects.create(name='Creator Delete WS', organization=self.org)
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{ws.pk}/',
            **_jwt(self.creator),
        )
        self.assertEqual(res.status_code, 204)
        ws.refresh_from_db()
        self.assertFalse(ws.is_active)
    def test_deleted_workspace_not_in_list(self):
        ws = Workspace.objects.create(name='Deleted List WS', organization=self.org)
        self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{ws.pk}/',
            **_jwt(self.admin),
        )
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        names = [w['name'] for w in res.data]
        self.assertNotIn('Deleted List WS', names)
    def test_workspace_from_other_org_returns_404(self):
        other_org = Organization.objects.create(name='Other Corp')
        other_ws = Workspace.objects.create(name='Other WS', organization=other_org)
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{other_ws.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 404)
# ── Workspace members ─────────────────────────────────────────────────────────
class WorkspaceMembersTest(BaseOrgAPI):
    def setUp(self):
        super().setUp()
        TeamMember.objects.create(
            workspace=self.workspace, user=self.admin, role=TeamMember.WORKSPACE_ADMIN
        )
    def test_list_workspace_members(self):
        res = self.client.get(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 1)
    def test_admin_can_add_org_member_to_workspace(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            {'user_id': self.member.pk, 'role': 'member'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(
            TeamMember.objects.filter(
                workspace=self.workspace, user=self.member
            ).exists()
        )
    def test_cannot_add_non_org_member_to_workspace(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            {'user_id': self.outsider.pk, 'role': 'member'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 400)
    def test_cannot_add_same_member_twice(self):
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.MEMBER
        )
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            {'user_id': self.member.pk, 'role': 'member'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 400)
    def test_update_workspace_member_role(self):
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.MEMBER
        )
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/{self.member.pk}/',
            {'role': 'manager'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(
            TeamMember.objects.filter(
                workspace=self.workspace, user=self.member, role='manager'
            ).exists()
        )
    def test_remove_workspace_member(self):
        TeamMember.objects.create(
            workspace=self.workspace, user=self.member, role=TeamMember.MEMBER
        )
        res = self.client.delete(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/{self.member.pk}/',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            TeamMember.objects.filter(
                workspace=self.workspace, user=self.member
            ).exists()
        )
    def test_plain_member_cannot_add_workspace_member(self):
        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            {'user_id': self.outsider.pk, 'role': 'member'},
            format='json',
            **_jwt(self.member),
        )
        self.assertEqual(res.status_code, 403)
    def test_nonexistent_workspace_member_returns_404(self):
        res = self.client.patch(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/99999/',
            {'role': 'manager'},
            format='json',
            **_jwt(self.admin),
        )
        self.assertEqual(res.status_code, 404)
    def test_workspace_admin_cannot_assign_workspace_admin_role(self):
        workspace_admin = _make_user('workspace_admin', 'wsadmin@example.com')
        OrganizationMember.objects.create(
            organization=self.org,
            user=workspace_admin,
            role=OrganizationMember.MEMBER,
        )
        TeamMember.objects.create(
            workspace=self.workspace,
            user=workspace_admin,
            role=TeamMember.WORKSPACE_ADMIN,
        )

        res = self.client.post(
            f'/api/v1/organizations/{self.org.pk}/workspaces/{self.workspace.pk}/members/',
            {'user_id': self.member.pk, 'role': TeamMember.WORKSPACE_ADMIN},
            format='json',
            **_jwt(workspace_admin),
        )
        self.assertEqual(res.status_code, 403)

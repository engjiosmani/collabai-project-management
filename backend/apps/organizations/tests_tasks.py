from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from apps.organizations.models import Organization, OrganizationInvite
from apps.organizations.tasks import send_invite_email


class SendInviteTaskTests(TestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_invite_email_runs(self):
        """Test that send_invite_email task executes without raising."""
        org = Organization.objects.create(name='Test Organization')
        invite = OrganizationInvite.objects.create(
            organization=org,
            email='newmember@example.com',
            token='11111111-1111-1111-1111-111111111111',
            expires_at=timezone.now() + timedelta(days=7),
        )
        # Task should run synchronously in eager mode and not raise
        result = send_invite_email(invite.id)
        self.assertIsNone(result)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_invite_email_handles_missing_invite(self):
        """Test that task handles non-existent invite gracefully."""
        # Call task with non-existent invite ID — should log warning and return
        result = send_invite_email(99999)
        self.assertIsNone(result)
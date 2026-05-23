from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.organizations.models import Organization, OrganizationInvite
from apps.user_profiles.models import PasswordResetToken

User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='http://testserver',
    DEFAULT_FROM_EMAIL='noreply@collabai.test',
)
class SendInviteEmailTaskTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.invite = OrganizationInvite.objects.create(
            organization=self.org,
            email='invitee@example.com',
            role=OrganizationInvite.MEMBER,
            token='test-token-abc',
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_invite_email_sent(self):
        from django.core import mail
        from apps.organizations.tasks import send_invite_email

        send_invite_email(self.invite.pk)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['invitee@example.com'])
        self.assertIn('Test Org', email.subject)
        self.assertIn('http://testserver/accept-invite/test-token-abc', email.body)

    def test_invite_email_missing_invite_does_not_raise(self):
        from apps.organizations.tasks import send_invite_email

        send_invite_email(999999)

    def test_invite_email_send_failure_does_not_raise(self):
        from apps.organizations.tasks import send_invite_email

        with patch('apps.organizations.tasks.EmailMultiAlternatives.send', side_effect=Exception('SMTP error')):
            send_invite_email(self.invite.pk)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='http://testserver',
    DEFAULT_FROM_EMAIL='noreply@collabai.test',
)
class SendPasswordResetEmailTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='pass1234!',
        )
        self.token = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_password_reset_email_sent(self):
        from django.core import mail
        from apps.core.tasks import send_password_reset_email

        send_password_reset_email(self.user.pk, str(self.token.token))

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['reset@example.com'])
        self.assertIn('Reset', email.subject)
        self.assertIn(f'http://testserver/reset-password?token={self.token.token}', email.body)

    def test_password_reset_email_missing_user_does_not_raise(self):
        from apps.core.tasks import send_password_reset_email

        send_password_reset_email(999999, 'fake-token')

    def test_password_reset_email_send_failure_does_not_raise(self):
        from apps.core.tasks import send_password_reset_email

        with patch('apps.core.tasks.EmailMultiAlternatives.send', side_effect=Exception('SMTP error')):
            send_password_reset_email(self.user.pk, str(self.token.token))

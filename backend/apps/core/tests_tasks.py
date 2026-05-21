from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.user_profiles.models import PasswordResetToken
from apps.core.tasks import send_password_reset_email

User = get_user_model()


class PasswordResetTaskTests(TestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_password_reset_email_runs(self):
        """Test that send_password_reset_email task executes without raising."""
        user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123!'
        )
        prt = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        # Task should run synchronously in eager mode and not raise
        result = send_password_reset_email(user.pk, str(prt.token))
        self.assertIsNone(result)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_password_reset_email_handles_missing_user(self):
        """Test that task handles non-existent user gracefully."""
        # Call task with non-existent user ID — should log warning and return
        result = send_password_reset_email(99999, '11111111-1111-1111-1111-111111111111')
        self.assertIsNone(result)
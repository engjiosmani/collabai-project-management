import logging
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from apps.user_profiles.models import PasswordResetToken

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True)
def send_password_reset_email(self, user_id, token_value):
    """
    Send password reset email for `user_id` containing `token_value`.
    Does not raise on failure; logs exceptions.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("send_password_reset_email: user %s not found", user_id)
        return

    try:
        # Retrieve token to show expiry if available
        expires_at = None
        try:
            prt = PasswordResetToken.objects.get(user=user, token=token_value)
            expires_at = prt.expires_at
        except PasswordResetToken.DoesNotExist:
            expires_at = None

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        context = {
            'token': token_value,
            'expires_at': expires_at,
            'frontend_url': frontend_url,
            'user': user,
        }

        subject = "Password reset request"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
        to = [user.email]

        text_body = render_to_string('emails/password_reset.txt', context)
        html_body = render_to_string('emails/password_reset.html', context)

        msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=to)
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Password reset email sent to %s", user.email)
    except Exception as exc:
        logger.exception("Failed to send password reset email to user %s: %s", user_id, exc)
        return
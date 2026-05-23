import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(bind=True)
def send_password_reset_email(self, user_id, token_value):
    """
    Send password reset email asynchronously.
    Logs failures without breaking the API flow.
    """

    try:
        user = User.objects.get(pk=user_id)

    except User.DoesNotExist:
        logger.warning(
            "send_password_reset_email: user %s not found",
            user_id,
        )
        return

    try:
        frontend_url = getattr(
            settings,
            "FRONTEND_URL",
            "http://localhost:3000",
        ).rstrip("/")

        reset_link = (
            f"{frontend_url}/reset-password?token={token_value}"
        )

        context = {
            "reset_link": reset_link,
            "user_email": user.email,
        }

        subject = "Reset your CollabAI password"

        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        text_body = render_to_string(
            "emails/password_reset.txt",
            context,
        )

        html_body = render_to_string(
            "emails/password_reset.html",
            context,
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=to_email,
        )

        msg.attach_alternative(
            html_body,
            "text/html",
        )

        msg.send()

        logger.info(
            "send_password_reset_email: sent to %s",
            user.email,
        )

    except Exception as exc:
        logger.error(
            "send_password_reset_email: failed for user %s — %s",
            user_id,
            exc,
            exc_info=True,
        )

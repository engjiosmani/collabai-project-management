import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_invite_email(self, invite_id):
    """
    Send organization invitation email asynchronously.
    Logs failures without breaking the API flow.
    """

    from .models import OrganizationInvite

    try:
        invite = (
            OrganizationInvite.objects
            .select_related("organization")
            .get(pk=invite_id)
        )

    except OrganizationInvite.DoesNotExist:
        logger.warning(
            "send_invite_email: invite %s not found",
            invite_id,
        )
        return

    try:
        frontend_url = getattr(
            settings,
            "FRONTEND_URL",
            "http://localhost:3000",
        ).rstrip("/")

        invite_link = (
            f"{frontend_url}/accept-invite/{invite.token}"
        )

        context = {
            "invite_link": invite_link,
            "organization_name": invite.organization.name,
            "invitee_email": invite.email,
        }

        subject = (
            f"You've been invited to join "
            f"{invite.organization.name} on CollabAI"
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [invite.email]

        text_body = render_to_string(
            "emails/invite.txt",
            context,
        )

        html_body = render_to_string(
            "emails/invite.html",
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
            "send_invite_email: sent to %s for org %s",
            invite.email,
            invite.organization.name,
        )

    except Exception as exc:
        logger.error(
            "send_invite_email: failed for invite %s — %s",
            invite_id,
            exc,
            exc_info=True,
        )


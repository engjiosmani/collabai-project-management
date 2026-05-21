import logging
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from .models import OrganizationInvite

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def send_invite_email(self, invite_id):
    """
    Asynchronously send an organization invite email.
    This task logs errors and returns on failure — it must not raise for API callers.
    """
    try:
        invite = OrganizationInvite.objects.select_related('organization').get(pk=invite_id)
    except OrganizationInvite.DoesNotExist:
        logger.warning("send_invite_email: invite %s not found", invite_id)
        return

    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        context = {
            'organization_name': invite.organization.name,
            'token': invite.token,
            'expires_at': invite.expires_at,
            'frontend_url': frontend_url,
        }

        subject = f"Invitation to join {invite.organization.name}"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
        to = [invite.email]

        text_body = render_to_string('emails/invite.txt', context)
        html_body = render_to_string('emails/invite.html', context)

        msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=to)
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Invite email sent to %s (invite=%s)", invite.email, invite_id)
    except Exception as exc:
        logger.exception("Failed to send invite email for invite %s: %s", invite_id, exc)
        # return quietly — do not bubble the exception
        return
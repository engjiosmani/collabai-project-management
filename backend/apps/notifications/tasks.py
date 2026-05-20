from celery import shared_task
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_email(self, user_email, subject, message):

    try:

        send_mail(
            subject=subject,
            message=message,
            from_email="admin@collabai.com",
            recipient_list=[user_email],
            fail_silently=False,
        )

        logger.info(f"Email sent successfully to {user_email}")

        return {
            "status": "success",
            "email": user_email,
        }

    except Exception as exc:

        logger.error(f"Email failed: {str(exc)}")

        raise self.retry(exc=exc, countdown=60)
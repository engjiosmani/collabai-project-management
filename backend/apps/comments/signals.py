from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import (
    invalidate_after_activity_log_change,
    invalidate_after_comment_change,
)

from .models import ActivityLog, Comment

from apps.notifications.models import Notification
from apps.notifications.tasks import send_notification_email


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def invalidate_comment_caches(sender, **kwargs):
    invalidate_after_comment_change()


@receiver(post_save, sender=ActivityLog)
@receiver(post_delete, sender=ActivityLog)
def invalidate_activity_log_caches(sender, **kwargs):
    invalidate_after_activity_log_change()


@receiver(post_save, sender=Comment)
def comment_notification(sender, instance, created, **kwargs):

    if not created:
        return

    task_owner = instance.task.created_by

    # mos i dergo email vetes
    if instance.author == task_owner:
        return

    message = f"New comment on task: {instance.task.title}"

    # notification ne databaze
    Notification.objects.create(
        user=task_owner,
        title="New Comment",
        message=message
    )

    # async email me celery
    send_notification_email.delay(
        task_owner.email,
        "New Comment",
        message
    )
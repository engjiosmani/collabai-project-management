from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_task_change

from .models import Task

from apps.notifications.models import Notification
from apps.notifications.tasks import send_notification_email


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_task_list_cache(sender, **kwargs):
    invalidate_after_task_change()


@receiver(post_save, sender=Task)
def task_notifications(sender, instance, created, **kwargs):

    if created and instance.assigned_to:

        message = f"You were assigned a new task: {instance.title}"

        # krijo notification ne databaze
        Notification.objects.create(
            user=instance.assigned_to,
            title="Task Assignment",
            message=message
        )

        # dergo email async me celery
        send_notification_email.delay(
            instance.assigned_to.email,
            "Task Assignment",
            message
        )
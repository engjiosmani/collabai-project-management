from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_notification_change

from .models import Notification


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def invalidate_notification_caches(sender, **kwargs):
    invalidate_after_notification_change()

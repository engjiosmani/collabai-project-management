from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import (
    invalidate_after_activity_log_change,
    invalidate_after_comment_change,
)

from .models import ActivityLog, Comment


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def invalidate_comment_caches(sender, **kwargs):
    invalidate_after_comment_change()


@receiver(post_save, sender=ActivityLog)
@receiver(post_delete, sender=ActivityLog)
def invalidate_activity_log_caches(sender, **kwargs):
    invalidate_after_activity_log_change()

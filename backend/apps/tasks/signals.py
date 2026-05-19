from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_task_change

from .models import Task


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_task_list_cache(sender, **kwargs):
    invalidate_after_task_change()

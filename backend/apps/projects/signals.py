from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_project_change

from .models import Project


@receiver(post_save, sender=Project)
@receiver(post_delete, sender=Project)
def invalidate_project_list_cache(sender, **kwargs):
    invalidate_after_project_change()

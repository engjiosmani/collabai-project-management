from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache import bump_version

from .models import Task
from .views import CACHE_NAMESPACE


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_task_list_cache(sender, **kwargs):
    bump_version(CACHE_NAMESPACE)

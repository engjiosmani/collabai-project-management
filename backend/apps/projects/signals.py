from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache import bump_version

from .models import Project
from .views import CACHE_NAMESPACE


@receiver(post_save, sender=Project)
@receiver(post_delete, sender=Project)
def invalidate_project_list_cache(sender, **kwargs):
    bump_version(CACHE_NAMESPACE)

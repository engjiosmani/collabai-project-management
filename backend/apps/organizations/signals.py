from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_organization_change

from .models import Organization


@receiver(post_save, sender=Organization)
@receiver(post_delete, sender=Organization)
def invalidate_organization_caches(sender, **kwargs):
    invalidate_after_organization_change()

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.cache_signals import invalidate_after_workspace_change

from .models import TeamMember, Workspace


@receiver(post_save, sender=Workspace)
@receiver(post_delete, sender=Workspace)
@receiver(post_save, sender=TeamMember)
@receiver(post_delete, sender=TeamMember)
def invalidate_workspace_caches(sender, **kwargs):
    invalidate_after_workspace_change()
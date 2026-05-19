import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'

    def ready(self):
        if os.environ.get('REDIS_URL'):
            return
        if 'test' in sys.argv:
            return
        logger.warning(
            'REDIS_URL is not set — using LocMem cache. '
            'Set REDIS_URL in backend/.env and run: python manage.py check_redis'
        )

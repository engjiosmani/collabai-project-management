from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from common.cache import cache_backend_label


class Command(BaseCommand):
    help = 'Verify REDIS_URL is set and the cache backend accepts read/write'

    def handle(self, *args, **options):
        label = cache_backend_label()
        if label != 'redis':
            self.stdout.write(
                self.style.WARNING(
                    'REDIS_URL is not configured — Django is using in-memory LocMem cache. '
                    'Set REDIS_URL in backend/.env (see .env.example) for production and course demos.'
                )
            )
            return

        try:
            cache.set('check_redis:ping', 'ok', timeout=10)
            value = cache.get('check_redis:ping')
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Redis unreachable: {exc}'))
            return

        if value != 'ok':
            self.stdout.write(self.style.ERROR('Redis read/write check failed.'))
            return

        location = settings.CACHES['default'].get('LOCATION', '')
        self.stdout.write(self.style.SUCCESS(f'Redis cache OK ({location})'))

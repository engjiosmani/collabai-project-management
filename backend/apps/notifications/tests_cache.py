from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import Notification


def _jwt(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'notifications-cache-tests',
    },
})
class NotificationListCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='notifcache@example.com',
            email='notifcache@example.com',
            password='x',
        )
        Notification.objects.create(user=self.user, title='Hello', message='World')
        self.client = APIClient()

    def test_notification_list_cached(self):
        url = '/api/v1/notifications/'
        with CaptureQueriesContext(connection) as first:
            self.client.get(url, **_jwt(self.user))
        with CaptureQueriesContext(connection) as second:
            self.client.get(url, **_jwt(self.user))
        self.assertLess(len(second.captured_queries), len(first.captured_queries))

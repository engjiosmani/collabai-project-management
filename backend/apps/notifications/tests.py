from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Notification

User = get_user_model()


def _jwt_header(user):
    return {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


class NotificationModelTest(TestCase):
    def test_create_notification(self):
        user = User.objects.create_user(username="notifyuser", password="test12345")

        notification = Notification.objects.create(
            user=user,
            title="Task assigned",
            message="You have been assigned a task"
        )

        self.assertEqual(notification.user, user)
        self.assertEqual(notification.title, "Task assigned")
        self.assertFalse(notification.is_read)


class NotificationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='n1@example.com', email='n1@example.com', password='x')
        self.other = User.objects.create_user(username='n2@example.com', email='n2@example.com', password='x')
        self.notification = Notification.objects.create(user=self.user, title='Hello', message='World')

    def test_list_scoped_to_user(self):
        Notification.objects.create(user=self.other, title='Other', message='Secret')
        res = self.client.get('/api/v1/notifications/', **_jwt_header(self.user))
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Hello')

    def test_crud_and_actions(self):
        create = self.client.post(
            '/api/v1/notifications/',
            {'title': 'New', 'message': 'Msg'},
            format='json',
            **_jwt_header(self.user),
        )
        self.assertEqual(create.status_code, 201, create.data)
        nid = create.data['id']

        mark_one = self.client.post(f'/api/v1/notifications/{nid}/mark_read/', **_jwt_header(self.user))
        self.assertEqual(mark_one.status_code, 200)
        self.assertTrue(mark_one.data['is_read'])

        Notification.objects.create(user=self.user, title='Another', message='M2')
        mark_all = self.client.post('/api/v1/notifications/mark_all_read/', **_jwt_header(self.user))
        self.assertEqual(mark_all.status_code, 200)
        self.assertGreaterEqual(mark_all.data['updated'], 1)

        listing = self.client.get('/api/v1/notifications/?is_read=true', **_jwt_header(self.user))
        self.assertEqual(listing.status_code, 200)

        delete = self.client.delete(f'/api/v1/notifications/{nid}/', **_jwt_header(self.user))
        self.assertEqual(delete.status_code, 204)

    def test_other_user_cannot_access_foreign_notification(self):
        res = self.client.get(f'/api/v1/notifications/{self.notification.pk}/', **_jwt_header(self.other))
        self.assertEqual(res.status_code, 404)

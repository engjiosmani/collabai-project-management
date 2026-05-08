from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


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
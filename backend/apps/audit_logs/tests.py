from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()


class AuditLogModelTest(TestCase):
    def test_create_audit_log(self):
        user = User.objects.create_user(username="audituser", password="test12345")

        audit_log = AuditLog.objects.create(
            user=user,
            action="CREATE",
            entity_name="Task",
            entity_id=1,
            metadata={"field": "title"}
        )

        self.assertEqual(audit_log.user, user)
        self.assertEqual(audit_log.action, "CREATE")
        self.assertEqual(audit_log.entity_name, "Task")
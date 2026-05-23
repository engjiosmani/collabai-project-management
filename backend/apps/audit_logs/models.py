from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.organizations.models import Organization


class AuditLog(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=150)
    entity_name = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["entity_name", "entity_id"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_name}"

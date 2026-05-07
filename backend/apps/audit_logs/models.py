from django.db import models
from django.conf import settings
from common.models import BaseModel


class AuditLog(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=150)
    entity_name = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["entity_name", "entity_id"])]

    def __str__(self):
        return f"{self.action} - {self.entity_name}"
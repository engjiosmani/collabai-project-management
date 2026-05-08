from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.tasks.models import Task


class AIRequest(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ai_requests")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_requests")
    prompt = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=50, default="pending")

    def __str__(self):
        return f"AI Request {self.id}"


class CacheEntity(BaseModel):
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField()
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key
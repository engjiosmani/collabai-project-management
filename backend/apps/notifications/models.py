from django.db import models
from django.conf import settings
from common.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return self.title
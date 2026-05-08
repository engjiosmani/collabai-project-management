from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.tasks.models import Task


class Comment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()

    def __str__(self):
        return f"Comment by {self.author}"


class ActivityLog(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["task", "created_at"])]

    def __str__(self):
        return self.action
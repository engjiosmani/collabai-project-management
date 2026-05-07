from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.projects.models import Project


class TaskStatus(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class TaskPriority(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    level = models.PositiveIntegerField(unique=True)

    def __str__(self):
        return self.name


class Label(BaseModel):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="#808080")

    def __str__(self):
        return self.name


class Task(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.ForeignKey(TaskStatus, on_delete=models.SET_NULL, null=True, related_name="tasks")
    priority = models.ForeignKey(TaskPriority, on_delete=models.SET_NULL, null=True, related_name="tasks")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return self.title


class TaskLabel(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_labels")
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="task_labels")

    class Meta:
        unique_together = ("task", "label")

    def __str__(self):
        return f"{self.task} - {self.label}"


class Attachment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to="attachments/")
    file_name = models.CharField(max_length=255)

    def __str__(self):
        return self.file_name
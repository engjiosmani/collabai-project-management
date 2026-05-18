from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.workspaces.models import Workspace
from common.tenant_queryset import TenantQuerySet

class Project(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    objects = TenantQuerySet.as_manager()

    class Meta:
        unique_together = ("workspace", "name")
        indexes = [models.Index(fields=["workspace", "name"])]

    def __str__(self):
        return self.name


class ProjectMember(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user} - {self.project}"


class Subscription(BaseModel):
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name="subscription")
    plan_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    objects = TenantQuerySet.as_manager()

    def __str__(self):
        return f"{self.workspace} - {self.plan_name}"


class Integration(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="integrations")
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=100)
    is_enabled = models.BooleanField(default=True)
    objects = TenantQuerySet.as_manager()

    class Meta:
        unique_together = ("workspace", "provider")

    def __str__(self):
        return f"{self.provider} integration"
from django.conf import settings
from django.db import models

from common.models import BaseModel
from apps.organizations.models import Organization


class Permission(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class Workspace(BaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workspaces"
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class JobRole(BaseModel):
 
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    task_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="AI task categories this role typically owns (e.g. backend, api, auth).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Role(BaseModel):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (MANAGER, "Manager"),
        (MEMBER, "Member"),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="roles"
    )
    name = models.CharField(
        max_length=100,
        choices=ROLE_CHOICES
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True
    )

    class Meta:
        unique_together = ("workspace", "name")

    def __str__(self):
        return f"{self.workspace.name} - {self.name}"


class TeamMember(BaseModel):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="team_members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
    )
    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
        help_text="Discipline used for AI task assignment (Backend, Frontend, DevOps, …).",
    )

    class Meta:
        unique_together = ("workspace", "user")

    def __str__(self):
        return f"{self.user} - {self.workspace}"
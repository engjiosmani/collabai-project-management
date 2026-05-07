from django.db import models
from django.conf import settings
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


class Role(BaseModel):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="roles"
    )
    name = models.CharField(max_length=100)
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
        related_name="team_members"
    )

    class Meta:
        unique_together = ("workspace", "user")

    def __str__(self):
        return f"{self.user} - {self.workspace}"


class WorkspaceInvite(BaseModel):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invites"
    )
    email = models.EmailField()
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workspace_invites"
    )
    token = models.CharField(max_length=255, unique=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("workspace", "email")

    def __str__(self):
        return f"Invite {self.email}"
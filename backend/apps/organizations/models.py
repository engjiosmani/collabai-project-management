from django.conf import settings
from django.db import models

from common.models import BaseModel


class Organization(BaseModel):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class OrganizationMember(BaseModel):
    OWNER = 'owner'
    ADMIN = 'admin'
    MANAGER = 'manager'
    MEMBER = 'member'

    ROLE_CHOICES = [
        (OWNER, 'Owner'),
        (ADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (MEMBER, 'Member'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=MEMBER
    )

    job_role = models.ForeignKey(
        'workspaces.JobRole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization_members',
    )

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f'{self.user_id} @ {self.organization.name} ({self.role})'
class OrganizationInvite(BaseModel):
    ORG_ADMIN = 'org_admin'
    WORKSPACE_ADMIN = 'workspace_admin'
    MANAGER = 'manager'
    MEMBER = 'member'

    ROLE_CHOICES = [
        (ORG_ADMIN, 'Organization Admin'),
        (WORKSPACE_ADMIN, 'Workspace Admin'),
        (MANAGER, 'Manager'),
        (MEMBER, 'Member'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invites',
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization_invites',
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=MEMBER,
    )
    token = models.CharField(max_length=255, unique=True)
    is_accepted = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ('organization', 'email')

    def __str__(self):
        return f'Invite {self.email} to {self.organization.name} as {self.role}'
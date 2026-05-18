from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction

from apps.organizations.models import Organization
from apps.workspaces.models import Role, TeamMember, Workspace

from .base_service import BaseService


class RegisterService(BaseService):
    @transaction.atomic
    def register_user(self, *, email: str, password: str):
        User = get_user_model()
        normalized = email.lower().strip()
        user = User.objects.create(
            username=normalized,
            email=normalized,
            password=make_password(password),
        )

        org, _ = Organization.objects.get_or_create(name='My Organization')
        workspace, _ = Workspace.objects.get_or_create(
            organization=org,
            name='My Workspace',
            defaults={'is_active': True},
        )
        member_role, _ = Role.objects.get_or_create(
            workspace=workspace,
            name=Role.MEMBER,
        )
        TeamMember.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={'role': member_role},
        )

        return user

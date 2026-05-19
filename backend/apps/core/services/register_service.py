from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project
from apps.workspaces.models import JobRole

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

        org, _ = Organization.objects.get_or_create(name='CollabAI')
        default_job_role = JobRole.objects.filter(code='full_stack_developer').first()
        OrganizationMember.objects.get_or_create(
            organization=org,
            user=user,
            defaults={'role': OrganizationMember.MEMBER, 'job_role': default_job_role},
        )
        Project.objects.get_or_create(
            organization=org,
            name='Demo Project',
            defaults={'description': 'Starter project for CollabAI', 'is_active': True},
        )

        return user

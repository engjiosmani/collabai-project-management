from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.organizations.models import Organization, OrganizationMember
from apps.projects.models import Project
from apps.workspaces.models import JobRole


class Command(BaseCommand):
    help = 'Create default organization membership and demo project for user(s).'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='User email to add as member')
        parser.add_argument('--org-name', type=str, default='CollabAI')

    def handle(self, *args, **options):
        email = options.get('email')
        org_name = options['org_name']

        org, _ = Organization.objects.get_or_create(name=org_name)
        default_job_role = JobRole.objects.filter(code='full_stack_developer').first()

        users = get_user_model().objects.all()
        if email:
            users = users.filter(email__iexact=email.strip())
            if not users.exists():
                self.stderr.write(self.style.ERROR(f'No user with email {email}'))
                return

        count = 0
        for user in users:
            _, added = OrganizationMember.objects.get_or_create(
                organization=org,
                user=user,
                defaults={'role': OrganizationMember.MEMBER, 'job_role': default_job_role},
            )
            if added:
                count += 1

        project, project_created = Project.objects.get_or_create(
            organization=org,
            name='Demo Project',
            defaults={'description': 'Starter project for CollabAI', 'is_active': True},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Organization "{org.name}" (id={org.pk}); {count} user(s) added as members; '
                f'project "{project.name}" (id={project.pk}) '
                f'{"created" if project_created else "exists"}.'
            )
        )

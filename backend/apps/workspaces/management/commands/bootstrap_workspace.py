from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.organizations.models import Organization
from apps.workspaces.models import Role, TeamMember, Workspace


class Command(BaseCommand):
    help = 'Create a default organization + workspace and add user(s) as members.'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='User email to add as member')
        parser.add_argument('--workspace-name', type=str, default='CollabAI')
        parser.add_argument('--org-name', type=str, default='CollabAI')

    def handle(self, *args, **options):
        email = options.get('email')
        workspace_name = options['workspace_name']
        org_name = options['org_name']

        org, _ = Organization.objects.get_or_create(name=org_name)
        workspace, created = Workspace.objects.get_or_create(
            organization=org,
            name=workspace_name,
            defaults={'is_active': True},
        )

        member_role, _ = Role.objects.get_or_create(
            workspace=workspace,
            name=Role.MEMBER,
        )

        users = get_user_model().objects.all()
        if email:
            users = users.filter(email__iexact=email.strip())
            if not users.exists():
                self.stderr.write(self.style.ERROR(f'No user with email {email}'))
                return

        count = 0
        for user in users:
            _, added = TeamMember.objects.get_or_create(
                workspace=workspace,
                user=user,
                defaults={'role': member_role},
            )
            if added:
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Workspace "{workspace.name}" (id={workspace.pk}) '
                f'{"created" if created else "exists"}; {count} user(s) added as members.'
            )
        )

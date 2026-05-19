from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deprecated: use bootstrap_organization instead.'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='User email to add as member')
        parser.add_argument('--org-name', type=str, default='CollabAI')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('bootstrap_workspace is deprecated; use bootstrap_organization.'))
        call_command(
            'bootstrap_organization',
            email=options.get('email'),
            org_name=options['org_name'],
        )

from django.core.management.base import BaseCommand

from apps.ai_assistant.tasks import reindex_organization
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = 'Index tasks, comments, projects, and activity logs for RAG.'

    def add_arguments(self, parser):
        parser.add_argument('--organization', type=int, help='Organization ID (optional)')
        parser.add_argument('--sync', action='store_true', help='Run synchronously without Celery queue')

    def handle(self, *args, **options):
        organization_id = options.get('organization')
        sync = options['sync']

        if organization_id:
            organizations = Organization.objects.filter(pk=organization_id)
        else:
            organizations = Organization.objects.all()

        for organization in organizations:
            self.stdout.write(f'Reindexing organization {organization.pk} ({organization.name})...')
            if sync:
                count = reindex_organization(organization.pk)
            else:
                reindex_organization.delay(organization.pk)
                count = '(queued)'
            self.stdout.write(self.style.SUCCESS(f'  -> {count}'))

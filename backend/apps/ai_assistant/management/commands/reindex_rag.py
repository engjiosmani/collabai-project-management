from django.core.management.base import BaseCommand

from apps.ai_assistant.tasks import reindex_workspace
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = 'Index tasks, comments, projects, and activity logs for RAG.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace', type=int, help='Workspace ID (optional)')
        parser.add_argument('--sync', action='store_true', help='Run synchronously without Celery queue')

    def handle(self, *args, **options):
        workspace_id = options.get('workspace')
        sync = options['sync']

        if workspace_id:
            workspaces = Workspace.objects.filter(pk=workspace_id)
        else:
            workspaces = Workspace.objects.all()

        for workspace in workspaces:
            self.stdout.write(f'Reindexing workspace {workspace.pk} ({workspace.name})...')
            if sync:
                count = reindex_workspace(workspace.pk)
            else:
                reindex_workspace.delay(workspace.pk)
                count = '(queued)'
            self.stdout.write(self.style.SUCCESS(f'  → {count}'))

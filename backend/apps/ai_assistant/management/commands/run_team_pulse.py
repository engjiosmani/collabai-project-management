from django.core.management.base import BaseCommand

from apps.ai_assistant.services.team_pulse import TeamPulseService


class Command(BaseCommand):
    help = 'Run Team Pulse daily standup for one workspace or all.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace-id', type=int, default=None)

    def handle(self, *args, **options):
        workspace_id = options['workspace_id']
        service = TeamPulseService()

        if workspace_id:
            workspaces = [workspace_id]
        else:
            from apps.workspaces.models import Workspace

            workspaces = list(
                Workspace.objects.filter(is_active=True).values_list('pk', flat=True)
            )

        for ws_id in workspaces:
            service.run_daily_standup(ws_id)
            self.stdout.write(self.style.SUCCESS(f'Standup done: workspace {ws_id}'))

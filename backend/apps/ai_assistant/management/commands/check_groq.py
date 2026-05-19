from django.core.management.base import BaseCommand

from apps.ai_assistant.services.groq_client import GroqClient


class Command(BaseCommand):
    help = 'Verify GROQ_API_KEY is loaded from backend/.env'

    def handle(self, *args, **options):
        client = GroqClient()
        if client.is_configured():
            self.stdout.write(self.style.SUCCESS('GROQ_API_KEY is configured.'))
            self.stdout.write(f'Model: {client.model}')
        else:
            self.stderr.write(
                self.style.ERROR(
                    'GROQ_API_KEY is missing. Create backend/.env from .env.example '
                    'and set GROQ_API_KEY=gsk_... then restart runserver.'
                )
            )

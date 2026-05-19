from django.core.management.base import BaseCommand

from apps.ai_assistant.services.groq_client import GroqClient


class Command(BaseCommand):
    help = 'Verify GROQ_API_KEY is loaded and accepted by the Groq API'

    def handle(self, *args, **options):
        client = GroqClient()
        if not client.is_configured():
            self.stderr.write(
                self.style.ERROR(
                    'GROQ_API_KEY is missing. Create backend/.env from .env.example '
                    'and set GROQ_API_KEY=gsk_... then restart runserver.'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('GROQ_API_KEY is configured.'))
        self.stdout.write(f'Model: {client.model}')

        try:
            reply = client.chat(
                system='Reply with one word only.',
                user='Say OK',
                max_tokens=8,
            )
            self.stdout.write(self.style.SUCCESS(f'Groq API OK (reply: {reply!r})'))
        except RuntimeError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            self.stderr.write(
                'Create a new key at https://console.groq.com/keys, '
                'update backend/.env, then restart runserver (Ctrl+C, then python manage.py runserver).'
            )

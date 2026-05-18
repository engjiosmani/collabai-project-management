from __future__ import annotations

from django.conf import settings


class GroqClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat(self, *, system: str, user: str) -> str:
        if not self.is_configured():
            raise RuntimeError(
                'GROQ_API_KEY mungon. Vendose në backend/.env (shiko .env.example).'
            )

        from groq import Groq

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return (response.choices[0].message.content or '').strip()

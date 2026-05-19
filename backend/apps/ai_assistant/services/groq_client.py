from __future__ import annotations

from django.conf import settings


class GroqClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError(
                'GROQ_API_KEY is missing. Set it in backend/.env (see .env.example).'
            )

        from groq import Groq

        client = Groq(api_key=self.api_key)
        kwargs = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if json_mode:
            kwargs['response_format'] = {'type': 'json_object'}

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            name = type(exc).__name__
            if 'Authentication' in name or getattr(exc, 'status_code', None) in (401, 403):
                raise RuntimeError(
                    'Invalid or expired GROQ_API_KEY. Update backend/.env and restart runserver.'
                ) from exc
            raise RuntimeError(f'Groq API error: {exc}') from exc
        return (response.choices[0].message.content or '').strip()

    def chat_messages(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError(
                'GROQ_API_KEY is missing. Set it in backend/.env (see .env.example).'
            )

        from groq import Groq

        client = Groq(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            name = type(exc).__name__
            if 'Authentication' in name or getattr(exc, 'status_code', None) in (401, 403):
                raise RuntimeError(
                    'Invalid or expired GROQ_API_KEY. Update backend/.env and restart runserver.'
                ) from exc
            raise RuntimeError(f'Groq API error: {exc}') from exc
        return (response.choices[0].message.content or '').strip()

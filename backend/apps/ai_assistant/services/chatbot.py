from __future__ import annotations

from typing import Any

from apps.ai_assistant.models import AIRequest

from .groq_client import GroqClient

CHATBOT_SYSTEM = """You are CollabAI ChatBot — a helpful general assistant in the CollabAI app.
Answer clearly and concisely. You do not have access to the user's projects, tasks, or internal data.
If they need answers from their project, suggest they open the AI Assistant page (project RAG chat).
Match the user's language when possible."""


class ChatBotService:
    def __init__(self, llm: GroqClient | None = None):
        self.llm = llm or GroqClient()

    def reply(
        self,
        *,
        user,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        text = (message or '').strip()
        if not text:
            raise ValueError('Message cannot be empty.')

        messages: list[dict[str, str]] = [{'role': 'system', 'content': CHATBOT_SYSTEM}]
        for turn in (history or [])[-12:]:
            role = turn.get('role')
            content = (turn.get('content') or '').strip()
            if role in ('user', 'assistant') and content:
                messages.append({'role': role, 'content': content})
        messages.append({'role': 'user', 'content': text})

        ai_request = AIRequest.objects.create(
            user=user,
            prompt=text,
            status='processing',
        )

        try:
            answer = self.llm.chat_messages(messages=messages, temperature=0.5, max_tokens=1024)
            ai_request.response = answer
            ai_request.status = 'completed'
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
        except Exception as exc:
            ai_request.status = 'failed'
            ai_request.response = str(exc)
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
            raise

        return {'answer': answer, 'request_id': ai_request.pk}

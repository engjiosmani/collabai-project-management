from __future__ import annotations

from typing import Any, Dict

from apps.ai_assistant.models import AIRequest

from .groq_client import GroqClient

ANALYSIS_MODES = frozenset({'summary', 'action_items', 'sentiment'})

SYSTEM_PROMPTS = {
    'summary': (
        'You are a concise technical writing assistant. '
        'Summarize the user text in clear English (3–6 bullet points or one short paragraph). '
        'Do not invent facts not present in the text.'
    ),
    'action_items': (
        'You are a project assistant. Extract actionable items from the user text. '
        'Return a markdown list; each item starts with "- [ ] ". '
        'If there are no clear actions, say so in one sentence.'
    ),
    'sentiment': (
        'You are an analyst. Classify overall tone of the user text as one of: '
        'positive, neutral, negative, or mixed. '
        'Reply with JSON only: {"label": "<one of the four>", "confidence": "low|medium|high", '
        '"rationale": "<one or two sentences>"}.'
    ),
}


class TextAnalysisService:
    def __init__(self, llm: GroqClient | None = None):
        self.llm = llm or GroqClient()

    def analyze(
        self,
        *,
        user,
        text: str,
        mode: str = 'summary',
        task_id: int | None = None,
        organization_id: int | None = None,
    ) -> Dict[str, Any]:
        if mode not in ANALYSIS_MODES:
            raise ValueError(f'Unsupported analysis mode: {mode}')

        ai_request = AIRequest.objects.create(
            user=user,
            organization_id=organization_id,
            task_id=task_id,
            prompt=f'[{mode}] {text[:2000]}',
            status='processing',
        )

        try:
            result = self.llm.chat(
                system=SYSTEM_PROMPTS[mode],
                user=text.strip(),
                temperature=0.2,
                max_tokens=1024,
                json_mode=(mode == 'sentiment'),
            )
            ai_request.response = result
            ai_request.status = 'completed'
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
        except Exception as exc:
            ai_request.status = 'failed'
            ai_request.response = str(exc)
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
            raise

        return {
            'mode': mode,
            'result': result,
            'request_id': ai_request.pk,
        }

from __future__ import annotations

from typing import Any, Dict, List

from django.conf import settings

from apps.ai_assistant.models import AIRequest

from .embeddings import EmbeddingService
from .groq_client import GroqClient
from .vector_store import get_vector_store

SYSTEM_PROMPT = """You are CollabAI — an internal project assistant.
Answer only using the project context provided below.
If the context is insufficient, say clearly that you have no data in the project for that topic.
Always respond in English.
End every answer with a "Sources:" section listing each source as [task #id], [comment #id], etc."""


class RAGService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        llm: GroqClient | None = None,
    ):
        self.embeddings = embedding_service or EmbeddingService()
        self.llm = llm or GroqClient()
        self.store = get_vector_store()

    def semantic_search(
        self,
        *,
        workspace_id: int,
        query: str,
        top_k: int | None = None,
    ) -> List[Dict[str, Any]]:
        k = top_k or settings.RAG_TOP_K_DEFAULT
        vector = self.embeddings.embed_text(query)
        hits = self.store.search(workspace_id=workspace_id, query_vector=vector, top_k=k)
        return [
            {
                'doc_type': hit.get('doc_type'),
                'doc_id': hit.get('doc_id'),
                'title': hit.get('title'),
                'content': hit.get('content'),
                'score': round(float(hit.get('score', 0)), 4),
            }
            for hit in hits
        ]

    def _format_context(self, hits: List[Dict[str, Any]]) -> str:
        if not hits:
            return '(No similar documents were found in this workspace.)'
        blocks = []
        for index, hit in enumerate(hits, start=1):
            blocks.append(
                f"[{index}] [{hit['doc_type']} #{hit['doc_id']}] {hit['title']}\n{hit['content']}"
            )
        return '\n\n'.join(blocks)

    def ask(
        self,
        *,
        user,
        workspace_id: int,
        question: str,
        top_k: int | None = None,
        task_id: int | None = None,
    ) -> Dict[str, Any]:
        hits = self.semantic_search(workspace_id=workspace_id, query=question, top_k=top_k)
        context = self._format_context(hits)

        user_prompt = f"""Project context (workspace {workspace_id}):
{context}

Question: {question}"""

        ai_request = AIRequest.objects.create(
            user=user,
            task_id=task_id,
            prompt=question,
            status='processing',
        )

        try:
            answer = self.llm.chat(system=SYSTEM_PROMPT, user=user_prompt)
            ai_request.response = answer
            ai_request.status = 'completed'
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
        except Exception as exc:
            ai_request.status = 'failed'
            ai_request.response = str(exc)
            ai_request.save(update_fields=['response', 'status', 'updated_at'])
            raise

        return {
            'answer': answer,
            'sources': hits,
            'request_id': ai_request.pk,
        }

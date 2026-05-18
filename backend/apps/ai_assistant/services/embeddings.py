from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Turn text into dense vectors (all-MiniLM-L6-v2 → 384 dims)."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.RAG_EMBEDDING_MODEL

    @lru_cache(maxsize=1)
    def _model(self):
        from sentence_transformers import SentenceTransformer

        logger.info('Loading embedding model %s', self.model_name)
        return SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * settings.RAG_EMBEDDING_DIMS
        vector = self._model().encode(text.strip(), normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.strip() if t else '' for t in texts]
        if not cleaned:
            return []
        vectors = self._model().encode(cleaned, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

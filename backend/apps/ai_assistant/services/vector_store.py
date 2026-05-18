from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, document: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete(self, doc_key: str) -> None:
        ...

    @abstractmethod
    def search(
        self,
        *,
        workspace_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        ...


class MemoryVectorStore(VectorStore):
    """Fallback for dev/tests when Redis Stack is unavailable."""

    _docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, document: Dict[str, Any]) -> None:
        key = document['id']
        self._docs[key] = document

    def delete(self, doc_key: str) -> None:
        self._docs.pop(doc_key, None)

    @classmethod
    def clear(cls) -> None:
        cls._docs = {}

    def search(
        self,
        *,
        workspace_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        ws = str(workspace_id)
        scored = []
        for doc in self._docs.values():
            if str(doc.get('workspace_id')) != ws:
                continue
            score = _cosine(query_vector, doc['embedding'])
            scored.append({**doc, 'score': score})
        scored.sort(key=lambda item: item['score'], reverse=True)
        return scored[:top_k]


class RedisVectorStore(VectorStore):
    """Redis Stack + RediSearch via redisvl."""

    def __init__(self):
        from redis import Redis
        from redisvl.index import SearchIndex
        from redisvl.schema import IndexSchema

        redis_url = settings.REDIS_URL
        if not redis_url:
            raise RuntimeError('REDIS_URL is required for RedisVectorStore')

        self._redis = Redis.from_url(redis_url, decode_responses=True)
        schema = IndexSchema.from_dict(
            {
                'index': {
                    'name': settings.RAG_VECTOR_INDEX_NAME,
                    'prefix': 'rag:doc:',
                },
                'fields': [
                    {'name': 'id', 'type': 'tag'},
                    {'name': 'workspace_id', 'type': 'tag'},
                    {'name': 'doc_type', 'type': 'tag'},
                    {'name': 'doc_id', 'type': 'tag'},
                    {'name': 'title', 'type': 'text'},
                    {'name': 'content', 'type': 'text'},
                    {
                        'name': 'embedding',
                        'type': 'vector',
                        'attrs': {
                            'dims': settings.RAG_EMBEDDING_DIMS,
                            'distance_metric': 'cosine',
                            'algorithm': 'flat',
                        },
                    },
                ],
            }
        )
        self._index = SearchIndex(schema, redis_client=self._redis)
        try:
            self._index.create(overwrite=False)
        except Exception as exc:
            logger.warning('Vector index create skipped: %s', exc)

    def upsert(self, document: Dict[str, Any]) -> None:
        self._index.load([document], keys=['id'])

    def delete(self, doc_key: str) -> None:
        self._index.delete([doc_key])

    def search(
        self,
        *,
        workspace_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        from redisvl.query import VectorQuery
        from redisvl.query.filter import Tag

        query = VectorQuery(
            vector=query_vector,
            vector_field_name='embedding',
            return_fields=['id', 'workspace_id', 'doc_type', 'doc_id', 'title', 'content'],
            num_results=top_k,
            filter_expression=Tag('workspace_id') == str(workspace_id),
        )
        raw = self._index.query(query)
        results = []
        for item in raw:
            vector_distance = item.get('vector_distance')
            score = 1.0 - float(vector_distance) if vector_distance is not None else 0.0
            results.append(
                {
                    'id': item.get('id'),
                    'workspace_id': item.get('workspace_id'),
                    'doc_type': item.get('doc_type'),
                    'doc_id': item.get('doc_id'),
                    'title': item.get('title'),
                    'content': item.get('content'),
                    'score': score,
                }
            )
        return results


_store: Optional[VectorStore] = None


def reset_vector_store() -> None:
    global _store
    _store = None
    MemoryVectorStore.clear()


def get_vector_store() -> VectorStore:
    global _store
    if _store is not None:
        return _store

    if settings.RAG_FORCE_MEMORY_STORE or not settings.REDIS_URL:
        logger.info('RAG using in-memory vector store')
        _store = MemoryVectorStore()
        return _store

    try:
        _store = RedisVectorStore()
        logger.info('RAG using Redis vector store')
        return _store
    except Exception as exc:
        logger.warning('Redis vector store unavailable (%s); using memory', exc)
        _store = MemoryVectorStore()
        return _store

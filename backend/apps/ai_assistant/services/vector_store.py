from __future__ import annotations

import logging
import math
import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

REDIS_DOC_PREFIX = "rag:doc:"


def _vector_to_float32_bytes(vector: Any) -> bytes:
    array = np.asarray(vector, dtype=np.float32)

    if array.ndim != 1:
        array = array.reshape(-1)

    expected_dims = settings.RAG_EMBEDDING_DIMS
    if array.size != expected_dims:
        raise ValueError(
            f"Embedding has {array.size} dimensions; expected {expected_dims}"
        )

    return array.tobytes()


def _decode_redis_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


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
        organization_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        ...


class MemoryVectorStore(VectorStore):
    """Fallback for dev/tests when Redis Stack is unavailable."""

    _docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, document: Dict[str, Any]) -> None:
        key = document["id"]
        self._docs[key] = document

    def delete(self, doc_key: str) -> None:
        self._docs.pop(doc_key, None)

    @classmethod
    def clear(cls) -> None:
        cls._docs = {}

    def search(
        self,
        *,
        organization_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:

        org = str(organization_id)

        scored = []

        for doc in self._docs.values():

            doc_org = str(
                doc.get("organization_id")
                or doc.get("workspace_id", "")
            )

            if doc_org != org:
                continue

            score = _cosine(
                query_vector,
                doc["embedding"]
            )

            scored.append({
                **doc,
                "score": score
            })

        scored.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return scored[:top_k]


class RedisVectorStore(VectorStore):
    """Redis Stack + RediSearch vector store."""

    def __init__(self):

        from redis import Redis
        from redisvl.index import SearchIndex
        from redisvl.schema import IndexSchema

        redis_url = settings.REDIS_URL

        if not redis_url:
            raise RuntimeError(
                "REDIS_URL is required for RedisVectorStore"
            )

        self._redis = Redis.from_url(
            redis_url,
            decode_responses=False
        )

        schema = IndexSchema.from_dict(
            {
                "index": {
                    "name": settings.RAG_VECTOR_INDEX_NAME,
                    "prefix": REDIS_DOC_PREFIX,
                },
                "fields": [
                    {
                        "name": "id",
                        "type": "tag",
                    },
                    {
                        "name": "organization_id",
                        "type": "tag",
                    },
                    {
                        "name": "doc_type",
                        "type": "tag",
                    },
                    {
                        "name": "doc_id",
                        "type": "tag",
                    },
                    {
                        "name": "title",
                        "type": "text",
                    },
                    {
                        "name": "content",
                        "type": "text",
                    },
                    {
                        "name": "embedding",
                        "type": "vector",
                        "attrs": {
                            "dims": settings.RAG_EMBEDDING_DIMS,
                            "distance_metric": "cosine",
                            "algorithm": "flat",
                            "datatype": "float32",
                        },
                    },
                ],
            }
        )

        self._index = SearchIndex(
            schema,
            redis_client=self._redis
        )

        try:
            self._index.create(overwrite=False)

        except Exception as exc:
            logger.warning(
                "Vector index create skipped: %s",
                exc
            )

    def upsert(
        self,
        document: Dict[str, Any]
    ) -> None:

        embedding_bytes = _vector_to_float32_bytes(
            document["embedding"]
        )

        redis_document = {
            "id": str(document["id"]),
            "organization_id": str(
                document["organization_id"]
            ),
            "doc_type": str(
                document["doc_type"]
            ),
            "doc_id": str(
                document["doc_id"]
            ),
            "title": str(
                document["title"]
            ),
            "content": str(
                document["content"]
            ),
            "embedding": embedding_bytes,
        }

        redis_key = (
            f"{REDIS_DOC_PREFIX}{document['id']}"
        )

        self._redis.hset(
            redis_key,
            mapping=redis_document
        )

    def delete(
        self,
        doc_key: str
    ) -> None:

        redis_key = (
            doc_key
            if doc_key.startswith(REDIS_DOC_PREFIX)
            else f"{REDIS_DOC_PREFIX}{doc_key}"
        )
        self._redis.delete(redis_key)

    def search(
        self,
        *,
        organization_id: int,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:

        from redisvl.query import VectorQuery
        from redisvl.query.filter import Tag

        query_vector_bytes = _vector_to_float32_bytes(
            query_vector
        )

        query = VectorQuery(
            vector=query_vector_bytes,
            vector_field_name="embedding",
            return_fields=[
                "id",
                "organization_id",
                "doc_type",
                "doc_id",
                "title",
                "content",
            ],
            num_results=top_k,
            filter_expression=(
                Tag("organization_id")
                == str(organization_id)
            ),
        )

        raw = self._index.query(query)

        results = []

        for item in raw:

            vector_distance = item.get(
                "vector_distance"
            )

            score = (
                1.0 - float(vector_distance)
                if vector_distance is not None
                else 0.0
            )

            results.append(
                {
                    "id": _decode_redis_value(
                        item.get("id")
                    ),
                    "organization_id": _decode_redis_value(
                        item.get("organization_id")
                    ),
                    "doc_type": _decode_redis_value(
                        item.get("doc_type")
                    ),
                    "doc_id": _decode_redis_value(
                        item.get("doc_id")
                    ),
                    "title": _decode_redis_value(
                        item.get("title")
                    ),
                    "content": _decode_redis_value(
                        item.get("content")
                    ),
                    "score": score,
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
        logger.info("RAG using in-memory vector store")
        _store = MemoryVectorStore()
        return _store

    try:
        _store = RedisVectorStore()
        logger.info("RAG using Redis vector store")
        return _store
    except Exception as exc:
        logger.warning(
            "Redis vector store unavailable (%s); using memory",
            exc
        )
        _store = MemoryVectorStore()
        return _store

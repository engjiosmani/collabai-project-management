from __future__ import annotations

from typing import Any, Dict, Optional

from apps.comments.models import ActivityLog, Comment
from apps.projects.models import Project
from apps.tasks.models import Task

from .embeddings import EmbeddingService


def _base_fields(*, organization_id: int, doc_type: str, doc_id: int, title: str, content: str) -> Dict[str, Any]:
    return {
        'id': f'{organization_id}:{doc_type}:{doc_id}',
        'organization_id': str(organization_id),
        'doc_type': doc_type,
        'doc_id': str(doc_id),
        'title': title[:500],
        'content': content[:8000],
    }


def document_from_task(task: Task) -> Dict[str, Any]:
    organization_id = task.project.organization_id
    content = f'{task.title}\n{task.description or ""}'.strip()
    return _base_fields(
        organization_id=organization_id,
        doc_type='task',
        doc_id=task.pk,
        title=task.title,
        content=content,
    )


def document_from_comment(comment: Comment) -> Dict[str, Any]:
    organization_id = comment.task.project.organization_id
    title = f'Comment on task #{comment.task_id}'
    return _base_fields(
        organization_id=organization_id,
        doc_type='comment',
        doc_id=comment.pk,
        title=title,
        content=comment.content,
    )


def document_from_project(project: Project) -> Dict[str, Any]:
    content = f'{project.name}\n{project.description or ""}'.strip()
    return _base_fields(
        organization_id=project.organization_id,
        doc_type='project',
        doc_id=project.pk,
        title=project.name,
        content=content,
    )


def document_from_activity(activity: ActivityLog) -> Dict[str, Any]:
    organization_id = activity.task.project.organization_id
    content = f'{activity.action}\n{activity.description or ""}'.strip()
    return _base_fields(
        organization_id=organization_id,
        doc_type='activity',
        doc_id=activity.pk,
        title=activity.action,
        content=content,
    )


def build_document(instance) -> Optional[Dict[str, Any]]:
    if isinstance(instance, Task):
        return document_from_task(instance)
    if isinstance(instance, Comment):
        return document_from_comment(instance)
    if isinstance(instance, Project):
        return document_from_project(instance)
    if isinstance(instance, ActivityLog):
        return document_from_activity(instance)
    return None


def index_instance(instance) -> str | None:
    doc = build_document(instance)
    if not doc:
        return None
    from .vector_store import get_vector_store

    embedding = EmbeddingService().embed_text(doc['content'])
    doc['embedding'] = embedding
    get_vector_store().upsert(doc)
    return doc['id']

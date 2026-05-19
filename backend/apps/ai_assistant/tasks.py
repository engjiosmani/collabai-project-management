from __future__ import annotations

import logging

from celery import shared_task
from django.apps import apps

from .services.indexing import build_document, index_instance

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def index_model_instance(self, app_label: str, model_name: str, pk: int) -> str | None:
    model = apps.get_model(app_label, model_name)
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return None

    doc_key = index_instance(instance)
    logger.info('Indexed %s:%s → %s', model_name, pk, doc_key)
    return doc_key


@shared_task
def delete_indexed_document(doc_key: str) -> None:
    from .services.vector_store import get_vector_store

    get_vector_store().delete(doc_key)


@shared_task
def reindex_workspace(workspace_id: int) -> int:
    from apps.comments.models import ActivityLog, Comment
    from apps.projects.models import Project
    from apps.tasks.models import Task

    count = 0
    for project in Project.objects.filter(workspace_id=workspace_id):
        index_instance(project)
        count += 1

    tasks = Task.objects.filter(project__workspace_id=workspace_id)
    for task in tasks:
        index_instance(task)
        count += 1

    for comment in Comment.objects.filter(task__project__workspace_id=workspace_id):
        index_instance(comment)
        count += 1

    for activity in ActivityLog.objects.filter(task__project__workspace_id=workspace_id):
        index_instance(activity)
        count += 1

    logger.info('Reindexed workspace %s (%s documents)', workspace_id, count)
    return count


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def generate_task_plan(self, plan_draft_id: int) -> int:
    from .services.task_generator import TaskGeneratorService

    try:
        TaskGeneratorService().run_generation(plan_draft_id)
    except Exception:
        # run_generation records FAILED on the draft; do not bubble to HTTP 500 when eager=True
        pass
    return plan_draft_id

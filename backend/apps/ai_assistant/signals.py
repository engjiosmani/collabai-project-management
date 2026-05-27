from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.comments.models import ActivityLog, Comment
from apps.projects.models import Project
from apps.tasks.models import Task

from .services.indexing import build_document
from .tasks import delete_indexed_document, index_model_instance

INDEXED_MODELS = (Task, Comment, Project, ActivityLog)
logger = logging.getLogger(__name__)


def _schedule_index(instance) -> None:
    if not settings.RAG_AUTO_INDEX:
        return
    if not settings.CELERY_TASK_ALWAYS_EAGER and not getattr(settings, 'REDIS_AVAILABLE', False):
        logger.warning('RAG auto-index skipped because Redis/Celery is unavailable.')
        return
    try:
        index_model_instance.delay(
            instance._meta.app_label,
            instance._meta.model_name,
            instance.pk,
        )
    except Exception as exc:
        logger.warning('RAG auto-index scheduling failed: %s', exc)


def _schedule_delete(instance) -> None:
    document = build_document(instance)
    if document:
        if not settings.CELERY_TASK_ALWAYS_EAGER and not getattr(settings, 'REDIS_AVAILABLE', False):
            logger.warning('RAG delete-index skipped because Redis/Celery is unavailable.')
            return
        try:
            delete_indexed_document.delay(document['id'])
        except Exception as exc:
            logger.warning('RAG delete-index scheduling failed: %s', exc)


def _connect_model(model):
    @receiver(post_save, sender=model)
    def on_save(sender, instance, **kwargs):
        _schedule_index(instance)

    @receiver(post_delete, sender=model)
    def on_delete(sender, instance, **kwargs):
        _schedule_delete(instance)


for _model in INDEXED_MODELS:
    _connect_model(_model)

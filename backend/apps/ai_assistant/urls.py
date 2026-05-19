from django.urls import path

from .views import AIRequestHistoryView, RAGQueryView, RAGReindexView, SemanticSearchView
from .views_task_generator import (
    AIConfigView,
    PlannedTaskRegenerateView,
    PlannedTaskUpdateView,
    TaskPlanApproveView,
    TaskPlanCreateView,
    TaskPlanDetailView,
    TaskPlanPreviewMarkdownView,
    TaskPlanRejectView,
    TaskPlanStatusView,
)

urlpatterns = [
    path('search/', SemanticSearchView.as_view(), name='ai-semantic-search'),
    path('query/', RAGQueryView.as_view(), name='ai-rag-query'),
    path('reindex/', RAGReindexView.as_view(), name='ai-rag-reindex'),
    path('history/', AIRequestHistoryView.as_view(), name='ai-request-history'),
    path('config/', AIConfigView.as_view(), name='ai-config'),
    # Task Generator (AI project plans)
    path('task-generator/plans/', TaskPlanCreateView.as_view(), name='ai-task-plan-create'),
    path('task-generator/plans/<int:plan_id>/', TaskPlanDetailView.as_view(), name='ai-task-plan-detail'),
    path(
        'task-generator/plans/<int:plan_id>/status/',
        TaskPlanStatusView.as_view(),
        name='ai-task-plan-status',
    ),
    path(
        'task-generator/plans/<int:plan_id>/approve/',
        TaskPlanApproveView.as_view(),
        name='ai-task-plan-approve',
    ),
    path(
        'task-generator/plans/<int:plan_id>/reject/',
        TaskPlanRejectView.as_view(),
        name='ai-task-plan-reject',
    ),
    path(
        'task-generator/plans/<int:plan_id>/preview-markdown/',
        TaskPlanPreviewMarkdownView.as_view(),
        name='ai-task-plan-preview',
    ),
    path(
        'task-generator/plans/<int:plan_id>/tasks/<int:task_id>/',
        PlannedTaskUpdateView.as_view(),
        name='ai-planned-task-update',
    ),
    path(
        'task-generator/plans/<int:plan_id>/tasks/<int:task_id>/regenerate/',
        PlannedTaskRegenerateView.as_view(),
        name='ai-planned-task-regenerate',
    ),
]

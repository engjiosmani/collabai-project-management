from django.urls import path

from .views import AIRequestHistoryView, RAGQueryView, RAGReindexView, SemanticSearchView

urlpatterns = [
    path('search/', SemanticSearchView.as_view(), name='ai-semantic-search'),
    path('query/', RAGQueryView.as_view(), name='ai-rag-query'),
    path('reindex/', RAGReindexView.as_view(), name='ai-rag-reindex'),
    path('history/', AIRequestHistoryView.as_view(), name='ai-request-history'),
]

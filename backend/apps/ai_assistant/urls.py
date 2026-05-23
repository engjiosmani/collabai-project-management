from django.urls import path

from .views import (
    AIRequestHistoryView,
    RAGQueryView,
    RAGReindexView,
    SemanticSearchView,
    TextAnalyzeView,
)
from .views.chatbot import ChatBotView
from .views.team_pulse import (
    AIConfigView,
    GitHubConfigView,
    TeamPulseOverviewView,
    TeamPulseRunView,
)

urlpatterns = [
    path('chatbot/', ChatBotView.as_view(), name='ai-chatbot'),
    path('analyze/', TextAnalyzeView.as_view(), name='ai-text-analyze'),
    path('search/', SemanticSearchView.as_view(), name='ai-semantic-search'),
    path('query/', RAGQueryView.as_view(), name='ai-rag-query'),
    path('reindex/', RAGReindexView.as_view(), name='ai-rag-reindex'),
    path('history/', AIRequestHistoryView.as_view(), name='ai-request-history'),
    path('config/', AIConfigView.as_view(), name='ai-config'),
    # Team Pulse: daily standup agent, GitHub commits
    path('team-pulse/', TeamPulseOverviewView.as_view(), name='ai-team-pulse'),
    path('team-pulse/github/', GitHubConfigView.as_view(), name='ai-team-pulse-github'),
    path('team-pulse/run/', TeamPulseRunView.as_view(), name='ai-team-pulse-run'),
]

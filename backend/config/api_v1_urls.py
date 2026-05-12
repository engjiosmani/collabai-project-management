from django.urls import include, path

from apps.core.views import DashboardSummaryView
from apps.tasks.views import TaskStatusViewSet

urlpatterns = [
    path('', include('apps.core.urls')),
    path('organizations/', include('apps.organizations.urls')),
    path('workspaces/', include('apps.workspaces.urls')),
    path('projects/', include('apps.projects.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('comments/', include('apps.comments.urls')),
    path('activity-logs/', include('apps.comments.activity_urls')),
    # Dashboard summary provides aggregated counts and recent activity
    path('dashboard/summary/', DashboardSummaryView.as_view()),
    path('notifications/', include('apps.notifications.urls')),
    path('ai/', include('apps.ai_assistant.urls')),
    path('audit/', include('apps.audit_logs.urls')),
    path('profiles/', include('apps.user_profiles.urls')),
    path('task-statuses/', TaskStatusViewSet.as_view({'get': 'list'}), name='task-statuses'),
]

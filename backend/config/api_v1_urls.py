from django.urls import include, path
from apps.core.views import DashboardSummaryView, HealthView, MetricsView
from apps.organizations.views import AcceptInviteView, MyInvitesView
from apps.tasks.views import TaskPriorityViewSet, TaskStatusViewSet

urlpatterns = [
    path('', include('apps.core.urls')),
    path('organizations/', include('apps.organizations.urls')),

    path('invites/my/', MyInvitesView.as_view(), name='my-invites'),
    path('invites/<str:token>/accept/', AcceptInviteView.as_view(), name='accept-invite'),

    path('job-roles/', include('apps.workspaces.job_roles_urls')),
    path('projects/', include('apps.projects.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('comments/', include('apps.comments.urls')),
    path('activity-logs/', include('apps.comments.activity_urls')),
    path('dashboard/summary/', DashboardSummaryView.as_view()),
    path('notifications/', include('apps.notifications.urls')),
    path('ai/', include('apps.ai_assistant.urls')),
    path('audit/', include('apps.audit_logs.urls')),
    path('users/', include('apps.user_profiles.urls')),
    path('profile/', include('apps.user_profiles.profile_urls')),
    path('health/', HealthView.as_view()),
    path('metrics/', MetricsView.as_view()),
    path(
        'task-statuses/',
        TaskStatusViewSet.as_view({'get': 'list'}),
        name='task-statuses',
    ),
    path(
        'task-priorities/',
        TaskPriorityViewSet.as_view({'get': 'list'}),
        name='task-priorities',
    ),
]
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaskStatusViewSet, TaskViewSet

router = DefaultRouter()
router.register('', TaskViewSet, basename='task')
router.register('task-statuses', TaskStatusViewSet, basename='task-status')

urlpatterns = [
    path('', include(router.urls)),
]
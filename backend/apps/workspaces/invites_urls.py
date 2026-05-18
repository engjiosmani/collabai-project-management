from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WorkspaceInviteViewSet

router = DefaultRouter()
router.register('', WorkspaceInviteViewSet, basename='workspace-invite')

urlpatterns = [
    path('', include(router.urls)),
]


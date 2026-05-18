from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PermissionViewSet

router = DefaultRouter()
router.register('', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]


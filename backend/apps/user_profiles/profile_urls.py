from django.urls import path
from .views import ChangePasswordView, MembershipsView, ProfileView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='profile-change-password'),
    path('memberships/', MembershipsView.as_view(), name='profile-memberships'),
]
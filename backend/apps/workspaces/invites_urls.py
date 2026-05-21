from django.urls import path
from apps.organizations.views import AcceptInviteView
urlpatterns = [
    path('<str:token>/accept/', AcceptInviteView.as_view(), name='accept-invite'),
]
from django.urls import path
from .views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    ResetPasswordView,
    TokenRefreshView,
)
urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/forgot-password', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='reset-password'),
]
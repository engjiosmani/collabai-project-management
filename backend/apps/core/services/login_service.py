from rest_framework_simplejwt.tokens import RefreshToken
from .base_service import BaseService


class LoginService(BaseService):
    def issue_tokens(self, *, user) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
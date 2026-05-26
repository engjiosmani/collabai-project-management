from rest_framework_simplejwt.tokens import RefreshToken


class LoginService:
    def issue_tokens(self, *, user) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

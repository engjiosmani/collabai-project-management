from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken


@extend_schema(
    tags=['Authentication'],
    request=RegisterSerializer,
    responses={
        201: RegisterSerializer,
        400: OpenApiResponse(description='Validation error'),
    },
    description='Register a new user with email and password.',
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    def get_success_headers(self, data):
        return {}

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        return response


@extend_schema(
    tags=['Authentication'],
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description='JWT access and refresh tokens'),
        400: OpenApiResponse(description='Invalid credentials'),
    },
    description='Authenticate with email and password; receive JWT tokens.',
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from .services.login_service import LoginService
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        tokens = LoginService().issue_tokens(user=serializer.validated_data['user'])
        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
    responses={
        200: OpenApiResponse(description='New access token'),
        400: OpenApiResponse(description='Invalid or expired refresh token'),
    },
    description='Obtain a new access token using a valid refresh token.',
)
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'refresh': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)}, status=status.HTTP_200_OK)
        except (TokenError, InvalidToken) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
    responses={
        204: OpenApiResponse(description='Logout successful'),
        400: OpenApiResponse(description='Invalid token or missing refresh token'),
    },
    description='Invalidate refresh token (server-side) by blacklisting it.',
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'refresh': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken):
            return Response({'detail': 'Invalid or expired refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)
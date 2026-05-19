from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers_chatbot import ChatBotRequestSerializer, ChatBotResponseSerializer
from .services.chatbot import ChatBotService


@extend_schema(
    tags=['AI / ChatBot'],
    request=ChatBotRequestSerializer,
    responses={
        200: ChatBotResponseSerializer,
        503: OpenApiResponse(description='LLM unavailable'),
    },
)
class ChatBotView(APIView):
    """General-purpose chat (no RAG, no project context)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatBotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = ChatBotService().reply(
                user=request.user,
                message=serializer.validated_data['message'],
                history=serializer.validated_data.get('history') or [],
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response(
                {'detail': f'Chat failed: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(payload)

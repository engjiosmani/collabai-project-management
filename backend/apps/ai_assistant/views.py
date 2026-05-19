from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.workspace_access import user_can_access_workspace

from .serializers import (
    AIRequestSerializer,
    RAGQuerySerializer,
    RAGSearchSerializer,
    ReindexSerializer,
)
from .services.rag import RAGService
from .tasks import reindex_workspace


class WorkspaceRAGMixin:
    permission_classes = [IsAuthenticated]

    def _assert_workspace_access(self, request, workspace_id: int) -> None:
        from apps.workspaces.models import Workspace

        workspace = Workspace.objects.filter(pk=workspace_id).first()
        if workspace is None:
            raise PermissionError('Workspace not found.')
        if workspace_id not in getattr(request, 'workspace_ids', []):
            if not user_can_access_workspace(request.user, workspace):
                raise PermissionError('You do not have access to this workspace.')


@extend_schema(
    tags=['AI / RAG'],
    request=RAGSearchSerializer,
    responses={200: OpenApiResponse(description='Semantic search hits')},
)
class SemanticSearchView(WorkspaceRAGMixin, APIView):
    """Semantic search (no LLM) for meaning-based task search."""

    def post(self, request):
        serializer = RAGSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace_id = serializer.validated_data['workspace_id']
        try:
            self._assert_workspace_access(request, workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        hits = RAGService().semantic_search(
            workspace_id=workspace_id,
            query=serializer.validated_data['query'],
            top_k=serializer.validated_data['top_k'],
        )
        return Response({'results': hits, 'count': len(hits)})


@extend_schema(
    tags=['AI / RAG'],
    request=RAGQuerySerializer,
    responses={200: OpenApiResponse(description='RAG answer with sources')},
)
class RAGQueryView(WorkspaceRAGMixin, APIView):
    """Question + vector DB context + Groq answer."""

    def post(self, request):
        serializer = RAGQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace_id = serializer.validated_data['workspace_id']
        try:
            self._assert_workspace_access(request, workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        try:
            payload = RAGService().ask(
                user=request.user,
                workspace_id=workspace_id,
                question=serializer.validated_data['question'],
                top_k=serializer.validated_data['top_k'],
                task_id=serializer.validated_data.get('task_id'),
            )
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload)


@extend_schema(
    tags=['AI / RAG'],
    request=ReindexSerializer,
    responses={202: OpenApiResponse(description='Reindex started')},
)
class RAGReindexView(WorkspaceRAGMixin, APIView):
    def post(self, request):
        serializer = ReindexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace_id = serializer.validated_data['workspace_id']
        try:
            self._assert_workspace_access(request, workspace_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        async_result = reindex_workspace.delay(workspace_id)
        return Response(
            {'detail': 'Reindex queued.', 'task_id': async_result.id},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=['AI / RAG'], responses={200: AIRequestSerializer(many=True)})
class AIRequestHistoryView(WorkspaceRAGMixin, APIView):
    def get(self, request):
        qs = request.user.ai_requests.order_by('-created_at')[:50]
        return Response(AIRequestSerializer(qs, many=True).data)

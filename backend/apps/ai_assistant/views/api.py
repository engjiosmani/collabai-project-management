from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import Task
from common.role_permissions import task_visibility_q
from common.tenant_access import user_can_access_organization

from ..serializers import (
    AIRequestSerializer,
    RAGQuerySerializer,
    RAGSearchSerializer,
    ReindexSerializer,
    TextAnalyzeResponseSerializer,
    TextAnalyzeSerializer,
)
from ..services.rag import RAGService
from ..services.text_analysis import TextAnalysisService
from ..tasks import reindex_organization


class OrganizationRAGMixin:
    permission_classes = [IsAuthenticated]

    def _assert_organization_access(self, request, organization_id: int) -> None:
        from apps.organizations.models import Organization

        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise PermissionError('Organization not found.')
        org_ids = getattr(request, 'organization_ids', [])
        if organization_id not in org_ids:
            if not user_can_access_organization(request.user, organization):
                raise PermissionError('You do not have access to this organization.')


WorkspaceRAGMixin = OrganizationRAGMixin


@extend_schema(
    tags=['AI / RAG'],
    request=RAGSearchSerializer,
    responses={200: OpenApiResponse(description='Semantic search hits')},
)
class SemanticSearchView(OrganizationRAGMixin, APIView):
    """Semantic search (no LLM) for meaning-based task search."""

    def post(self, request):
        serializer = RAGSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data['organization_id']
        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        hits = RAGService().semantic_search(
            organization_id=organization_id,
            query=serializer.validated_data['query'],
            top_k=serializer.validated_data['top_k'],
        )
        return Response({'results': hits, 'count': len(hits)})


@extend_schema(
    tags=['AI / RAG'],
    request=RAGQuerySerializer,
    responses={200: OpenApiResponse(description='RAG answer with sources')},
)
class RAGQueryView(OrganizationRAGMixin, APIView):
    """Question + vector DB context + Groq answer."""

    def post(self, request):
        serializer = RAGQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data['organization_id']
        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        try:
            task_id = serializer.validated_data.get('task_id')
            if task_id is not None:
                task = Task.objects.filter(
                    task_visibility_q(request.user, [organization_id]),
                    pk=task_id,
                    project__organization_id=organization_id,
                    project__is_active=True,
                ).first()
                if task is None:
                    return Response(
                        {'task_id': ['Invalid task for this organization.']},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            payload = RAGService().ask(
                user=request.user,
                organization_id=organization_id,
                question=serializer.validated_data['question'],
                top_k=serializer.validated_data['top_k'],
                task_id=task_id,
            )
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response(
                {'detail': f'AI request failed: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(payload)


@extend_schema(
    tags=['AI / RAG'],
    request=ReindexSerializer,
    responses={202: OpenApiResponse(description='Reindex started')},
)
class RAGReindexView(OrganizationRAGMixin, APIView):
    def post(self, request):
        serializer = ReindexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data['organization_id']
        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        async_result = reindex_organization.delay(organization_id)
        return Response(
            {'detail': 'Reindex queued.', 'task_id': async_result.id},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    tags=['AI / Text analysis'],
    request=TextAnalyzeSerializer,
    responses={
        200: TextAnalyzeResponseSerializer,
        503: OpenApiResponse(description='LLM unavailable or misconfigured'),
    },
)
class TextAnalyzeView(OrganizationRAGMixin, APIView):
    """Analyze arbitrary text via the configured LLM (summary, action items, sentiment)."""

    def post(self, request):
        serializer = TextAnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task_id = data.get('task_id')
        organization_id = getattr(request, 'active_organization_id', None)
        if task_id is not None:
            task = Task.objects.filter(
                task_visibility_q(request.user, getattr(request, 'organization_ids', [])),
                pk=task_id,
                project__is_active=True,
            ).select_related('project').first()
            if task is None:
                return Response(
                    {'task_id': ['Invalid task or access denied.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            organization_id = task.project.organization_id

        try:
            payload = TextAnalysisService().analyze(
                user=request.user,
                text=data['text'],
                mode=data['mode'],
                task_id=task_id,
                organization_id=organization_id,
            )
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response(
                {'detail': f'Text analysis failed: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(payload)


@extend_schema(tags=['AI / RAG'], responses={200: AIRequestSerializer(many=True)})
class AIRequestHistoryView(OrganizationRAGMixin, APIView):
    def get(self, request):
        qs = request.user.ai_requests.select_related('organization').order_by('-created_at')
        org_id = request.query_params.get('organization_id') or getattr(
            request,
            'active_organization_id',
            None,
        )
        if org_id:
            try:
                org_id = int(org_id)
            except (TypeError, ValueError):
                return Response(
                    {'organization_id': ['Invalid organization_id.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                self._assert_organization_access(request, org_id)
            except PermissionError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(organization_id=org_id)
        qs = qs[:50]
        return Response(AIRequestSerializer(qs, many=True).data)

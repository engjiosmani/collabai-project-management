from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_assistant.services.groq_client import GroqClient

from .models import PlannedTask, ProjectPlanDraft
from .serializers_task_generator import (
    AIConfigSerializer,
    ApproveTaskPlanSerializer,
    CreateTaskPlanSerializer,
    PlannedTaskSerializer,
    PlannedTaskUpdateSerializer,
    ProjectPlanDraftSerializer,
    ProjectPlanStatusSerializer,
    RegenerateTaskSerializer,
    TaskPlanApproveResponseSerializer,
    TaskPlanCreateResponseSerializer,
    TaskPlanErrorResponseSerializer,
    TaskPlanPreviewMarkdownSerializer,
)
from .services.task_generator.project_target import resolve_target_project
from .services.task_generator import PlanMaterializer, TaskGeneratorService
from .tasks import generate_task_plan
from .views import OrganizationRAGMixin


@extend_schema(
    tags=['AI / Task Generator'],
    responses={200: AIConfigSerializer},
)
class AIConfigView(APIView):
    """Check whether Groq is configured (for UI diagnostics)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        configured = GroqClient().is_configured()
        return Response(
            {
                'groq_configured': configured,
                'groq_model': settings.GROQ_MODEL,
                'hint': (
                    None
                    if configured
                    else 'Set GROQ_API_KEY in backend/.env, then restart runserver.'
                ),
            }
        )


class TaskPlanMixin(OrganizationRAGMixin):
    def _get_plan(self, request, plan_id: int) -> ProjectPlanDraft:
        plan = get_object_or_404(
            ProjectPlanDraft.objects.select_related('target_project').prefetch_related('planned_tasks'),
            pk=plan_id,
            user=request.user,
        )
        try:
            self._assert_organization_access(request, plan.organization_id)
        except PermissionError as exc:
            raise PermissionError(str(exc)) from exc
        return plan


@extend_schema(
    tags=['AI / Task Generator'],
    request=CreateTaskPlanSerializer,
    responses={
        202: TaskPlanCreateResponseSerializer,
        403: TaskPlanErrorResponseSerializer,
        503: TaskPlanErrorResponseSerializer,
    },
)
class TaskPlanCreateView(TaskPlanMixin, APIView):
    """Create a draft plan and start async generation (Prompt 1 + 2)."""

    def post(self, request):
        serializer = CreateTaskPlanSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data['organization_id']
        try:
            self._assert_organization_access(request, organization_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        from apps.workspaces.services.team_members import team_members_payload_for_organization

        team_members = serializer.validated_data.get('team_members') or []
        if not team_members:
            team_members = team_members_payload_for_organization(organization_id)

        target_project_id = serializer.validated_data.get('target_project_id')
        target_project = None
        if target_project_id:
            target_project = resolve_target_project(
                organization_id=organization_id,
                project_id=target_project_id,
                user=request.user,
                request=request,
            )

        draft = ProjectPlanDraft.objects.create(
            user=request.user,
            organization_id=organization_id,
            input_description=serializer.validated_data['description'],
            sprint_count=serializer.validated_data['sprint_count'],
            team_members=team_members,
            target_project=target_project,
            status=ProjectPlanDraft.Status.DRAFT,
        )

        if not TaskGeneratorService().llm.is_configured():
            draft.status = ProjectPlanDraft.Status.FAILED
            draft.error_message = 'GROQ_API_KEY is missing. Set it in backend/.env.'
            draft.save(update_fields=['status', 'error_message', 'updated_at'])
            return Response(
                {'detail': draft.error_message, 'plan_id': draft.pk},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        generate_task_plan.delay(draft.pk)
        draft.refresh_from_db()

        if draft.status == ProjectPlanDraft.Status.FAILED:
            return Response(
                {
                    'detail': draft.error_message or 'Plan generation failed.',
                    'plan_id': draft.pk,
                    'status': draft.status,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Eager Celery finishes in delay(); do not overwrite PENDING_APPROVAL back to GENERATING.
        if draft.status == ProjectPlanDraft.Status.DRAFT:
            draft.status = ProjectPlanDraft.Status.GENERATING
            draft.save(update_fields=['status', 'updated_at'])

        return Response(
            {
                'plan_id': draft.pk,
                'status': draft.status,
                'detail': 'Task plan generation started.',
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=['AI / Task Generator'], responses={200: ProjectPlanDraftSerializer})
class TaskPlanDetailView(TaskPlanMixin, APIView):
    def get(self, request, plan_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(ProjectPlanDraftSerializer(plan).data)


@extend_schema(tags=['AI / Task Generator'], responses={200: ProjectPlanStatusSerializer})
class TaskPlanStatusView(TaskPlanMixin, APIView):
    def get(self, request, plan_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(ProjectPlanStatusSerializer(plan).data)


@extend_schema(
    tags=['AI / Task Generator'],
    request=ApproveTaskPlanSerializer,
    responses={
        200: TaskPlanApproveResponseSerializer,
        400: TaskPlanErrorResponseSerializer,
        403: TaskPlanErrorResponseSerializer,
    },
)
class TaskPlanApproveView(TaskPlanMixin, APIView):
    def post(self, request, plan_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        approve_serializer = ApproveTaskPlanSerializer(
            data=request.data or {},
            context={'plan': plan, 'request': request},
        )
        approve_serializer.is_valid(raise_exception=True)
        if 'target_project_id' in approve_serializer.validated_data:
            override_project_id = approve_serializer.validated_data['target_project_id']
            if override_project_id:
                plan.target_project = resolve_target_project(
                    organization_id=plan.organization_id,
                    project_id=override_project_id,
                    user=request.user,
                    request=request,
                )
            else:
                plan.target_project = None
            plan.save(update_fields=['target_project', 'updated_at'])

        try:
            project = PlanMaterializer().approve(plan)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        created_new = getattr(project, '_created_new_for_plan', True)
        detail = (
            'Plan approved; tasks were added to the existing project.'
            if not created_new
            else 'Plan approved; a new project and tasks were created.'
        )
        return Response(
            {
                'detail': detail,
                'project_id': project.pk,
                'project_name': project.name,
                'created_new_project': created_new,
                'tasks_created': plan.planned_tasks.count(),
                'plan': ProjectPlanDraftSerializer(plan).data,
            }
        )


@extend_schema(
    tags=['AI / Task Generator'],
    responses={
        204: OpenApiResponse(description='Plan rejected'),
        400: TaskPlanErrorResponseSerializer,
        403: TaskPlanErrorResponseSerializer,
    },
)
class TaskPlanRejectView(TaskPlanMixin, APIView):
    def delete(self, request, plan_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if plan.status == ProjectPlanDraft.Status.SYNCED:
            return Response(
                {'detail': 'Cannot reject a plan that is already synced.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.status = ProjectPlanDraft.Status.REJECTED
        plan.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['AI / Task Generator'],
    request=PlannedTaskUpdateSerializer,
    responses={
        200: PlannedTaskSerializer,
        400: TaskPlanErrorResponseSerializer,
        403: TaskPlanErrorResponseSerializer,
    },
)
class PlannedTaskUpdateView(TaskPlanMixin, APIView):
    def patch(self, request, plan_id: int, task_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if plan.status != ProjectPlanDraft.Status.PENDING_APPROVAL:
            return Response(
                {'detail': 'Tasks can only be edited while the plan is pending approval.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        planned = get_object_or_404(PlannedTask, pk=task_id, plan=plan)
        serializer = PlannedTaskUpdateSerializer(planned, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PlannedTaskSerializer(planned).data)


@extend_schema(
    tags=['AI / Task Generator'],
    request=RegenerateTaskSerializer,
    responses={
        200: PlannedTaskSerializer,
        400: TaskPlanErrorResponseSerializer,
        403: TaskPlanErrorResponseSerializer,
        503: TaskPlanErrorResponseSerializer,
    },
)
class PlannedTaskRegenerateView(TaskPlanMixin, APIView):
    """Prompt 3 — enrich a single task."""

    def post(self, request, plan_id: int, task_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if plan.status != ProjectPlanDraft.Status.PENDING_APPROVAL:
            return Response(
                {'detail': 'Tasks can only be regenerated while the plan is pending approval.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        planned = get_object_or_404(PlannedTask, pk=task_id, plan=plan)
        body = RegenerateTaskSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        service = TaskGeneratorService()
        if not service.llm.is_configured():
            return Response(
                {'detail': 'GROQ_API_KEY is missing.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        plan_json = plan.ai_raw_output or {}
        try:
            service.regenerate_single_task(
                plan=plan_json,
                slug=planned.slug,
                team_members=plan.team_members or [],
                hint=body.validated_data.get('hint', ''),
            )
        except (ValueError, RuntimeError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.ai_raw_output = plan_json
        plan.save(update_fields=['ai_raw_output', 'updated_at'])

        enriched = next(
            t
            for sprint in plan_json.get('sprints', [])
            for t in sprint.get('tasks', [])
            if t.get('slug') == planned.slug
        )
        service.update_single_planned_task(planned, enriched, planned.sprint_number)
        planned.refresh_from_db()
        return Response(PlannedTaskSerializer(planned).data)


@extend_schema(
    tags=['AI / Task Generator'],
    responses={
        200: TaskPlanPreviewMarkdownSerializer,
        403: TaskPlanErrorResponseSerializer,
    },
)
class TaskPlanPreviewMarkdownView(TaskPlanMixin, APIView):
    def get(self, request, plan_id: int):
        try:
            plan = self._get_plan(request, plan_id)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        bodies = [
            {'slug': t.slug, 'title': t.title, 'body': t.rendered_body}
            for t in plan.planned_tasks.order_by('order')
        ]
        return Response({'tasks': bodies, 'count': len(bodies)})

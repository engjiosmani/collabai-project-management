from rest_framework import serializers

from apps.workspaces.models import Workspace

from .models import PlannedTask, ProjectPlanDraft
from .services.task_generator.project_target import resolve_target_project


class TeamMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField(max_length=150)
    role = serializers.CharField(max_length=100)


class CreateTaskPlanSerializer(serializers.Serializer):
    workspace_id = serializers.IntegerField()
    description = serializers.CharField(max_length=8000)
    sprint_count = serializers.IntegerField(min_value=1, max_value=6, default=3)
    team_members = TeamMemberSerializer(many=True, required=False, default=list)
    target_project_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_workspace_id(self, value):
        if not Workspace.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Workspace not found.')
        return value

    def validate(self, attrs):
        project_id = attrs.get('target_project_id')
        if not project_id:
            return attrs
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        workspace_id = attrs['workspace_id']
        try:
            resolve_target_project(
                workspace_id=workspace_id,
                project_id=project_id,
                user=user,
                request=request,
            )
        except PermissionError as exc:
            raise serializers.ValidationError({'target_project_id': str(exc)}) from exc
        except ValueError as exc:
            raise serializers.ValidationError({'target_project_id': str(exc)}) from exc
        return attrs


class ApproveTaskPlanSerializer(serializers.Serializer):
    target_project_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_target_project_id(self, value):
        if value is None:
            return value
        plan = self.context.get('plan')
        request = self.context.get('request')
        if plan is None or request is None:
            return value
        try:
            resolve_target_project(
                workspace_id=plan.workspace_id,
                project_id=value,
                user=request.user,
                request=request,
            )
        except PermissionError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class PlannedTaskSerializer(serializers.ModelSerializer):
    suggested_assignee_user_id = serializers.IntegerField(
        source='suggested_assignee_id',
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = PlannedTask
        fields = (
            'id',
            'slug',
            'title',
            'category',
            'sprint_number',
            'story_points',
            'labels',
            'suggested_assignee_user_id',
            'suggested_assignee_role',
            'depends_on',
            'covers_requirements',
            'goal',
            'description',
            'subtasks',
            'acceptance_criteria',
            'technical_notes',
            'rendered_body',
            'order',
            'is_edited',
        )
        read_only_fields = (
            'id',
            'slug',
            'rendered_body',
            'order',
        )


class PlannedTaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlannedTask
        fields = (
            'title',
            'goal',
            'description',
            'subtasks',
            'acceptance_criteria',
            'story_points',
            'labels',
            'suggested_assignee_role',
        )

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.is_edited = True
        from apps.ai_assistant.prompts import render_task_body

        username = instance.suggested_assignee.username if instance.suggested_assignee else None
        instance.rendered_body = render_task_body(
            instance.to_task_dict(),
            instance.sprint_number,
            username,
        )
        instance.save(update_fields=['is_edited', 'rendered_body', 'updated_at'])
        return instance


class RegenerateTaskSerializer(serializers.Serializer):
    hint = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class ProjectPlanDraftSerializer(serializers.ModelSerializer):
    planned_tasks = PlannedTaskSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()
    scope_tag_count = serializers.SerializerMethodField()
    target_project_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPlanDraft
        fields = (
            'id',
            'workspace',
            'input_description',
            'sprint_count',
            'team_members',
            'status',
            'ai_raw_output',
            'validation_meta',
            'error_message',
            'target_project_id',
            'target_project_name',
            'project',
            'approved_at',
            'synced_at',
            'created_at',
            'updated_at',
            'planned_tasks',
            'task_count',
            'scope_tag_count',
        )
        read_only_fields = fields

    def get_target_project_name(self, obj):
        if obj.target_project_id:
            return obj.target_project.name
        return None

    def get_task_count(self, obj):
        return obj.planned_tasks.count()

    def get_scope_tag_count(self, obj):
        tags = set()
        for task in obj.planned_tasks.all():
            for tag in task.covers_requirements or []:
                tags.add(str(tag))
        return len(tags)


class ProjectPlanStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlanDraft
        fields = ('id', 'status', 'error_message', 'validation_meta', 'updated_at')

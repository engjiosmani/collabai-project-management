from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.organizations.models import Organization


class AIRequest(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ai_requests")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_requests")
    prompt = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=50, default="pending")

    def __str__(self):
        return f"AI Request {self.id}"


class CacheEntity(BaseModel):
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField()
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key


class ProjectPlanDraft(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        GENERATING = 'GENERATING', 'Generating'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending approval'
        APPROVED = 'APPROVED', 'Approved'
        SYNCING = 'SYNCING', 'Syncing'
        SYNCED = 'SYNCED', 'Synced'
        REJECTED = 'REJECTED', 'Rejected'
        FAILED = 'FAILED', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_plan_drafts',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='project_plan_drafts',
    )
    input_description = models.TextField()
    sprint_count = models.PositiveSmallIntegerField(default=3)
    team_members = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    ai_raw_output = models.JSONField(default=dict, blank=True)
    validation_meta = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    target_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_plan_drafts',
        help_text='If set, approval adds tasks to this project instead of creating a new one.',
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plan_drafts',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = (self.ai_raw_output or {}).get('project_name') or f'Plan #{self.pk}'
        return f'{name} ({self.status})'


class PlannedTask(BaseModel):
    plan = models.ForeignKey(
        ProjectPlanDraft,
        on_delete=models.CASCADE,
        related_name='planned_tasks',
    )
    slug = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=64, blank=True)
    sprint_number = models.PositiveSmallIntegerField(default=1)
    story_points = models.PositiveSmallIntegerField(default=3)
    labels = models.JSONField(default=list, blank=True)
    suggested_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planned_task_assignments',
    )
    suggested_assignee_role = models.CharField(max_length=100, blank=True)
    depends_on = models.JSONField(default=list, blank=True)
    covers_requirements = models.JSONField(default=list, blank=True)
    goal = models.TextField(blank=True)
    description = models.TextField(blank=True)
    subtasks = models.JSONField(default=list, blank=True)
    acceptance_criteria = models.JSONField(default=list, blank=True)
    technical_notes = models.TextField(blank=True)
    rendered_body = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_edited = models.BooleanField(default=False)
    created_task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_planned_tasks',
    )

    class Meta:
        ordering = ['order', 'slug']
        unique_together = ('plan', 'slug')

    def __str__(self):
        return self.slug

    def to_task_dict(self) -> dict:
        return {
            'slug': self.slug,
            'title': self.title,
            'category': self.category,
            'labels': self.labels,
            'story_points': self.story_points,
            'suggested_assignee_user_id': self.suggested_assignee_id,
            'suggested_assignee_role': self.suggested_assignee_role,
            'depends_on': self.depends_on,
            'covers_requirements': self.covers_requirements,
            'goal': self.goal,
            'description': self.description,
            'subtasks': self.subtasks,
            'acceptance_criteria': self.acceptance_criteria,
            'technical_notes': self.technical_notes,
        }


class GitHubOrganizationConfig(BaseModel):
    """Per-organization GitHub PAT + repos for commit sync in standups."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='github_config',
    )
    access_token = models.CharField(max_length=255, blank=True)
    repos = models.JSONField(
        default=list,
        blank=True,
        help_text='List of "owner/repo" strings.',
    )
    member_github_logins = models.JSONField(
        default=dict,
        blank=True,
        help_text='Map of user_id (str) → GitHub username.',
    )
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f'GitHub config for organization {self.organization_id}'


class TeamPulseAlert(BaseModel):
    class AlertType(models.TextChoices):
        BURNOUT_RISK = 'burnout_risk', 'Burnout risk'
        CAPACITY_AVAILABLE = 'capacity_available', 'Capacity available'
        REBALANCE_SUGGESTION = 'rebalance_suggestion', 'Rebalance suggestion'

    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        SUGGESTION = 'suggestion', 'Suggestion'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='team_pulse_alerts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_pulse_alerts',
    )
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_pulse_alerts_about',
    )
    alert_type = models.CharField(max_length=32, choices=AlertType.choices, db_index=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARNING)
    title = models.CharField(max_length=200)
    message = models.TextField()
    metrics = models.JSONField(default=dict, blank=True)
    is_dismissed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'is_dismissed', 'created_at'])]


class TeamPulseReport(BaseModel):
    class ReportType(models.TextChoices):
        WORKLOAD = 'workload', 'Workload analysis'
        STANDUP = 'standup', 'Daily standup'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='team_pulse_reports',
    )
    report_type = models.CharField(max_length=16, choices=ReportType.choices, db_index=True)
    summary_markdown = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'report_type', 'created_at'])]
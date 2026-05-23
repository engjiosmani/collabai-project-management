from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.tasks.models import Task
from apps.organizations.models import Organization


class AIRequest(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ai_requests")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_requests',
    )
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_requests")
    prompt = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=50, default="pending")

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'user', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"AI Request {self.id}"


class CacheEntity(BaseModel):
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField()
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key


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

from django.contrib import admin

from .models import (
    AIRequest,
    CacheEntity,
    GitHubOrganizationConfig,
    PlannedTask,
    ProjectPlanDraft,
    TeamPulseAlert,
    TeamPulseReport,
)


class PlannedTaskInline(admin.TabularInline):
    model = PlannedTask
    extra = 0
    readonly_fields = ('slug', 'title', 'sprint_number', 'story_points')


@admin.register(ProjectPlanDraft)
class ProjectPlanDraftAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [PlannedTaskInline]


admin.site.register(AIRequest)
admin.site.register(CacheEntity)
admin.site.register(GitHubOrganizationConfig)
admin.site.register(TeamPulseAlert)
admin.site.register(TeamPulseReport)

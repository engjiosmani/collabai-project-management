from django.contrib import admin

from .models import (
    AIRequest,
    CacheEntity,
    GitHubOrganizationConfig,
    TeamPulseAlert,
    TeamPulseReport,
)


admin.site.register(AIRequest)
admin.site.register(CacheEntity)
admin.site.register(GitHubOrganizationConfig)
admin.site.register(TeamPulseAlert)
admin.site.register(TeamPulseReport)

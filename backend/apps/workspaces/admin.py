from django.contrib import admin

from .models import JobRole,TeamMember, Workspace


admin.site.register(Workspace)
admin.site.register(JobRole)
admin.site.register(TeamMember)
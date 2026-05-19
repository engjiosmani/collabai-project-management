from django.contrib import admin

from .models import JobRole, Permission, Role, TeamMember, Workspace, WorkspaceInvite

admin.site.register(Workspace)
admin.site.register(Role)
admin.site.register(JobRole)
admin.site.register(Permission)
admin.site.register(TeamMember)
admin.site.register(WorkspaceInvite)
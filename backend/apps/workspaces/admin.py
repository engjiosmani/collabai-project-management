from django.contrib import admin
from .models import Workspace, Role, Permission, TeamMember, WorkspaceInvite

admin.site.register(Workspace)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(TeamMember)
admin.site.register(WorkspaceInvite)
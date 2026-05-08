from django.contrib import admin
from .models import Project, ProjectMember, Subscription, Integration

admin.site.register(Project)
admin.site.register(ProjectMember)
admin.site.register(Subscription)
admin.site.register(Integration)
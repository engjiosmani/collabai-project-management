from django.contrib import admin
from .models import Comment, ActivityLog

admin.site.register(Comment)
admin.site.register(ActivityLog)
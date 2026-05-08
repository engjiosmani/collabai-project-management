from django.contrib import admin
from .models import Task, TaskStatus, TaskPriority, Label, TaskLabel, Attachment

admin.site.register(Task)
admin.site.register(TaskStatus)
admin.site.register(TaskPriority)
admin.site.register(Label)
admin.site.register(TaskLabel)
admin.site.register(Attachment)
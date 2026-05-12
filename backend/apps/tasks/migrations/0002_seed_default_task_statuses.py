from django.db import migrations


def seed_default_statuses(apps, schema_editor):
    TaskStatus = apps.get_model('tasks', 'TaskStatus')
    defaults = ['To Do', 'In Progress', 'Done']
    for name in defaults:
        TaskStatus.objects.get_or_create(name=name)


def unseed_default_statuses(apps, schema_editor):
    TaskStatus = apps.get_model('tasks', 'TaskStatus')
    TaskStatus.objects.filter(name__in=['To Do', 'In Progress', 'Done']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_default_statuses, reverse_code=unseed_default_statuses),
    ]



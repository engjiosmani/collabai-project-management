from django.db import migrations


def backfill_ai_request_organization(apps, schema_editor):
    AIRequest = apps.get_model('ai_assistant', 'AIRequest')

    requests = AIRequest.objects.select_related('task__project').filter(
        organization__isnull=True,
        task__project__organization_id__isnull=False,
    )
    for ai_request in requests.iterator():
        ai_request.organization_id = ai_request.task.project.organization_id
        ai_request.save(update_fields=['organization'])


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0010_airequest_organization_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_ai_request_organization, migrations.RunPython.noop),
    ]

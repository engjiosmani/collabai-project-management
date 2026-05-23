from django.db import migrations


def scope_existing_labels(apps, schema_editor):
    Label = apps.get_model('tasks', 'Label')
    TaskLabel = apps.get_model('tasks', 'TaskLabel')

    label_cache = {}
    task_labels = TaskLabel.objects.select_related('task__project', 'label').filter(
        task__project__organization_id__isnull=False,
        label__isnull=False,
    )

    for task_label in task_labels.iterator():
        source = task_label.label
        org_id = task_label.task.project.organization_id
        if source.organization_id == org_id:
            continue

        key = (org_id, source.name.lower())
        target = label_cache.get(key)
        if target is None:
            target = Label.objects.filter(
                organization_id=org_id,
                name__iexact=source.name,
            ).first()
            if target is None:
                target = Label.objects.create(
                    organization_id=org_id,
                    name=source.name,
                    color=source.color,
                )
            label_cache[key] = target

        if task_label.label_id != target.id:
            task_label.label_id = target.id
            task_label.save(update_fields=['label'])


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_label_organization_and_more'),
    ]

    operations = [
        migrations.RunPython(scope_existing_labels, migrations.RunPython.noop),
    ]

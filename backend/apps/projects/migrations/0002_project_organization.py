import django.db.models.deletion
from django.db import migrations, models


def copy_workspace_to_organization(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    Subscription = apps.get_model('projects', 'Subscription')
    Integration = apps.get_model('projects', 'Integration')

    for project in Project.objects.select_related('workspace').iterator():
        project.organization_id = project.workspace.organization_id
        project.save(update_fields=['organization_id'])

    for sub in Subscription.objects.select_related('workspace').iterator():
        sub.organization_id = sub.workspace.organization_id
        sub.save(update_fields=['organization_id'])

    for integration in Integration.objects.select_related('workspace').iterator():
        integration.organization_id = integration.workspace.organization_id
        integration.save(update_fields=['organization_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_organizationmember'),
        ('projects', '0001_initial'),
        ('workspaces', '0006_alter_jobrole_task_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projects',
                to='organizations.organization',
            ),
        ),
        migrations.AddField(
            model_name='subscription',
            name='organization',
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subscription',
                to='organizations.organization',
            ),
        ),
        migrations.AddField(
            model_name='integration',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrations',
                to='organizations.organization',
            ),
        ),
        migrations.RunPython(copy_workspace_to_organization, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='integration',
            unique_together=set(),
        ),
        migrations.RemoveIndex(
            model_name='project',
            name='projects_pr_workspa_25ee67_idx',
        ),
        migrations.RemoveField(model_name='project', name='workspace'),
        migrations.RemoveField(model_name='subscription', name='workspace'),
        migrations.RemoveField(model_name='integration', name='workspace'),
        migrations.AlterField(
            model_name='project',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projects',
                to='organizations.organization',
            ),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='organization',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subscription',
                to='organizations.organization',
            ),
        ),
        migrations.AlterField(
            model_name='integration',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrations',
                to='organizations.organization',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together={('organization', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='integration',
            unique_together={('organization', 'provider')},
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['organization', 'name'], name='projects_pr_organiz_6f3a21_idx'),
        ),
    ]

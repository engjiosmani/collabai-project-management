import django.db.models.deletion
from django.db import migrations, models


def workspace_fk_to_organization(apps, schema_editor):
    ProjectPlanDraft = apps.get_model('ai_assistant', 'ProjectPlanDraft')
    TeamPulseAlert = apps.get_model('ai_assistant', 'TeamPulseAlert')
    TeamPulseReport = apps.get_model('ai_assistant', 'TeamPulseReport')
    GitHubWorkspaceConfig = apps.get_model('ai_assistant', 'GitHubWorkspaceConfig')

    for draft in ProjectPlanDraft.objects.select_related('workspace').iterator():
        draft.organization_id = draft.workspace.organization_id
        draft.save(update_fields=['organization_id'])

    for alert in TeamPulseAlert.objects.select_related('workspace').iterator():
        alert.organization_id = alert.workspace.organization_id
        alert.save(update_fields=['organization_id'])

    for report in TeamPulseReport.objects.select_related('workspace').iterator():
        report.organization_id = report.workspace.organization_id
        report.save(update_fields=['organization_id'])

    for cfg in GitHubWorkspaceConfig.objects.select_related('workspace').iterator():
        cfg.organization_id = cfg.workspace.organization_id
        cfg.save(update_fields=['organization_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0007_delete_standupdeliveryconfig'),
        ('organizations', '0002_organizationmember'),
        ('projects', '0002_project_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectplandraft',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='project_plan_drafts',
                to='organizations.organization',
            ),
        ),
        migrations.AddField(
            model_name='teampulsealert',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='team_pulse_alerts',
                to='organizations.organization',
            ),
        ),
        migrations.AddField(
            model_name='teampulsereport',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='team_pulse_reports',
                to='organizations.organization',
            ),
        ),
        migrations.AddField(
            model_name='githubworkspaceconfig',
            name='organization',
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='github_config',
                to='organizations.organization',
            ),
        ),
        migrations.RunPython(workspace_fk_to_organization, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name='teampulsereport',
            name='ai_assistan_workspa_8a1f2d_idx',
        ),
        migrations.RemoveIndex(
            model_name='teampulsealert',
            name='ai_assistan_workspa_4c9e1a_idx',
        ),
        migrations.RemoveField(model_name='projectplandraft', name='workspace'),
        migrations.RemoveField(model_name='teampulsealert', name='workspace'),
        migrations.RemoveField(model_name='teampulsereport', name='workspace'),
        migrations.RemoveField(model_name='githubworkspaceconfig', name='workspace'),
        migrations.AlterField(
            model_name='projectplandraft',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='project_plan_drafts',
                to='organizations.organization',
            ),
        ),
        migrations.AlterField(
            model_name='teampulsealert',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='team_pulse_alerts',
                to='organizations.organization',
            ),
        ),
        migrations.AlterField(
            model_name='teampulsereport',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='team_pulse_reports',
                to='organizations.organization',
            ),
        ),
        migrations.AlterField(
            model_name='githubworkspaceconfig',
            name='organization',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='github_config',
                to='organizations.organization',
            ),
        ),
        migrations.RenameModel(
            old_name='GitHubWorkspaceConfig',
            new_name='GitHubOrganizationConfig',
        ),
        migrations.AddIndex(
            model_name='teampulsereport',
            index=models.Index(
                fields=['organization', 'report_type', 'created_at'],
                name='ai_assistan_organiz_8a1f2d_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='teampulsealert',
            index=models.Index(
                fields=['organization', 'is_dismissed', 'created_at'],
                name='ai_assistan_organiz_4c9e1a_idx',
            ),
        ),
    ]

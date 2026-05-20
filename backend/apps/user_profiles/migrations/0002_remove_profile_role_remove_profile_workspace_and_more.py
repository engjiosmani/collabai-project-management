

import django.db.models.deletion
from django.db import migrations, models


def copy_workspace_organization_to_profile(apps, schema_editor):
    Profile = apps.get_model('user_profiles', 'Profile')

    for profile in Profile.objects.select_related('workspace__organization').all():
        if profile.workspace_id and profile.workspace and profile.workspace.organization_id:
            profile.organization_id = profile.workspace.organization_id
            profile.save(update_fields=['organization'])


def reverse_copy_workspace_organization_to_profile(apps, schema_editor):
    # Reverse is intentionally no-op because one organization can have many workspaces,
    # so we cannot safely infer the original workspace from organization alone.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0003_alter_organizationmember_role_organizationinvite'),
        ('user_profiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profiles',
                to='organizations.organization',
            ),
        ),
        migrations.RunPython(
            copy_workspace_organization_to_profile,
            reverse_copy_workspace_organization_to_profile,
        ),
        migrations.RemoveField(
            model_name='profile',
            name='role',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='workspace',
        ),
    ]
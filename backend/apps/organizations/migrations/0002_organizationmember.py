import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_team_members_to_org_members(apps, schema_editor):
    TeamMember = apps.get_model('workspaces', 'TeamMember')
    OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
    for tm in TeamMember.objects.select_related('workspace', 'role').iterator():
        ws = tm.workspace
        role_key = 'member'
        if tm.role_id and tm.role.name:
            role_key = str(tm.role.name).lower()
        if role_key not in ('admin', 'manager', 'member'):
            role_key = 'member'
        OrganizationMember.objects.get_or_create(
            organization_id=ws.organization_id,
            user_id=tm.user_id,
            defaults={'role': role_key, 'job_role_id': tm.job_role_id},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('workspaces', '0006_alter_jobrole_task_categories'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(
                    choices=[('admin', 'Admin'), ('manager', 'Manager'), ('member', 'Member')],
                    default='member',
                    max_length=20,
                )),
                ('job_role', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='organization_members',
                    to='workspaces.jobrole',
                )),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='members',
                    to='organizations.organization',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='organization_memberships',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('organization', 'user')},
            },
        ),
        migrations.RunPython(copy_team_members_to_org_members, migrations.RunPython.noop),
    ]

from django.db import migrations, models


def migrate_team_member_roles_forward(apps, schema_editor):
    """Copy role name from the Role FK into role_temp CharField.
    Role.name == 'admin'   -> 'workspace_admin'
    Role.name == 'manager' -> 'manager'
    Role.name == 'member'  -> 'member'
    role is NULL           -> 'member'
    """
    TeamMember = apps.get_model('workspaces', 'TeamMember')
    ROLE_MAP = {
        'admin': 'workspace_admin',
        'manager': 'manager',
        'member': 'member',
    }
    for tm in TeamMember.objects.select_related('role').all():
        if tm.role is not None:
            mapped = ROLE_MAP.get(tm.role.name, 'member')
        else:
            mapped = 'member'
        tm.role_temp = mapped
        tm.save(update_fields=['role_temp'])


def copy_temp_to_role_forward(apps, schema_editor):
    TeamMember = apps.get_model('workspaces', 'TeamMember')
    for tm in TeamMember.objects.all():
        tm.role = tm.role_temp or 'member'
        tm.save(update_fields=['role'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False  # Required: RunPython + DDL in same migration causes pending trigger error on PostgreSQL

    dependencies = [
        ('workspaces', '0007_delete_workspaceinvite'),
    ]

    operations = [
        # 1. Add temp field
        migrations.AddField(
            model_name='teammember',
            name='role_temp',
            field=models.CharField(max_length=20, default='member'),
        ),

        # 2. Populate temp from FK
        migrations.RunPython(migrate_team_member_roles_forward, reverse_code=noop),

        # 3. Remove old FK
        migrations.RemoveField(
            model_name='teammember',
            name='role',
        ),

        # 4. Add new CharField
        migrations.AddField(
            model_name='teammember',
            name='role',
            field=models.CharField(
                choices=[
                    ('workspace_admin', 'Workspace Admin'),
                    ('manager', 'Manager'),
                    ('member', 'Member'),
                ],
                default='member',
                max_length=20,
            ),
        ),

        # 5. Copy temp -> new role
        migrations.RunPython(copy_temp_to_role_forward, reverse_code=noop),

        # 6. Remove temp field
        migrations.RemoveField(
            model_name='teammember',
            name='role_temp',
        ),

        # 7. Remove M2M between Role and Permission
        migrations.RemoveField(
            model_name='role',
            name='permissions',
        ),

        # 8. Delete Role model
        migrations.DeleteModel(name='Role'),

        # 9. Delete Permission model
        migrations.DeleteModel(name='Permission'),
    ]
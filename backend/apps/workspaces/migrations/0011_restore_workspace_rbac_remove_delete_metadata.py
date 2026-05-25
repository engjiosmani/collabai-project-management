from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0010_add_workspace_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workspace',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='workspace',
            name='deleted_at',
        ),
    ]

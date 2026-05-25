from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0006_organization_deleted_at_organization_deleted_by_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='organization',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='organization',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='organization',
            name='is_deleted',
        ),
    ]

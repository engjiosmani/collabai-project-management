from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0011_backfill_ai_request_organization'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GitHubOrganizationConfig',
        ),
        migrations.DeleteModel(
            name='TeamPulseAlert',
        ),
        migrations.DeleteModel(
            name='TeamPulseReport',
        ),
    ]

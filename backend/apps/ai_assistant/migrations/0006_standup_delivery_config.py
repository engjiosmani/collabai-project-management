import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0006_alter_jobrole_task_categories'),
        ('ai_assistant', '0005_team_pulse'),
    ]

    operations = [
        migrations.CreateModel(
            name='StandupDeliveryConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notify_in_app', models.BooleanField(
                    default=True,
                    help_text='Create in-app notifications for each team member.',
                )),
                ('slack_webhook_url', models.CharField(blank=True, max_length=500)),
                ('discord_webhook_url', models.CharField(blank=True, max_length=500)),
                ('email_enabled', models.BooleanField(
                    default=False,
                    help_text='Email standup summary to workspace members (requires SMTP in settings).',
                )),
                ('email_extra_recipients', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='Additional email addresses (list of strings).',
                )),
                ('workspace', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='standup_delivery',
                    to='workspaces.workspace',
                )),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

# Generated manually for Team Pulse feature

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0006_alter_jobrole_task_categories'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_assistant', '0004_alter_projectplandraft_target_project'),
    ]

    operations = [
        migrations.CreateModel(
            name='GitHubWorkspaceConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('access_token', models.CharField(blank=True, max_length=255)),
                ('repos', models.JSONField(blank=True, default=list, help_text='List of "owner/repo" strings.')),
                ('member_github_logins', models.JSONField(blank=True, default=dict, help_text='Map of user_id (str) → GitHub username.')),
                ('is_enabled', models.BooleanField(default=False)),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='github_config', to='workspaces.workspace')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TeamPulseReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report_type', models.CharField(choices=[('workload', 'Workload analysis'), ('standup', 'Daily standup')], db_index=True, max_length=16)),
                ('summary_markdown', models.TextField(blank=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('period_start', models.DateTimeField(blank=True, null=True)),
                ('period_end', models.DateTimeField(blank=True, null=True)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_pulse_reports', to='workspaces.workspace')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TeamPulseAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('alert_type', models.CharField(choices=[('burnout_risk', 'Burnout risk'), ('capacity_available', 'Capacity available'), ('rebalance_suggestion', 'Rebalance suggestion')], db_index=True, max_length=32)),
                ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('suggestion', 'Suggestion')], default='warning', max_length=16)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('metrics', models.JSONField(blank=True, default=dict)),
                ('is_dismissed', models.BooleanField(default=False)),
                ('related_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_pulse_alerts_about', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_pulse_alerts', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_pulse_alerts', to='workspaces.workspace')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='teampulsereport',
            index=models.Index(fields=['workspace', 'report_type', 'created_at'], name='ai_assistan_workspa_8a1f2d_idx'),
        ),
        migrations.AddIndex(
            model_name='teampulsealert',
            index=models.Index(fields=['workspace', 'is_dismissed', 'created_at'], name='ai_assistan_workspa_4c9e1a_idx'),
        ),
    ]

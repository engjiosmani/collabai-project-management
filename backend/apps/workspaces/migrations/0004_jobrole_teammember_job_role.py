# Generated manually for JobRole catalog

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0003_alter_role_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('task_categories', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.AddField(
            model_name='teammember',
            name='job_role',
            field=models.ForeignKey(
                blank=True,
                help_text='Discipline used for AI task assignment (Backend, Frontend, DevOps, …).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='team_members',
                to='workspaces.jobrole',
            ),
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
        ('ai_assistant', '0002_task_generator'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectplandraft',
            name='target_project',
            field=models.ForeignKey(
                blank=True,
                help_text='When set, approved tasks are added to this project instead of creating a new one.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='task_plan_drafts',
                to='projects.project',
            ),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0006_standup_delivery_config'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StandupDeliveryConfig',
        ),
    ]

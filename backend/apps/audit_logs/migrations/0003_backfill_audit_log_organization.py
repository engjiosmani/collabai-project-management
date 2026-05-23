from django.db import migrations


def backfill_audit_log_organization(apps, schema_editor):
    AuditLog = apps.get_model('audit_logs', 'AuditLog')

    for log in AuditLog.objects.filter(organization__isnull=True).iterator():
        metadata = log.metadata or {}
        org_id = metadata.get('organization_id')
        if org_id:
            log.organization_id = org_id
            log.save(update_fields=['organization'])


class Migration(migrations.Migration):

    dependencies = [
        ('audit_logs', '0002_auditlog_organization_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_audit_log_organization, migrations.RunPython.noop),
    ]

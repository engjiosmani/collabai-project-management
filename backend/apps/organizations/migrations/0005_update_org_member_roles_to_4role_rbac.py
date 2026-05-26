from django.db import migrations, models


def migrate_org_member_roles_forward(apps, schema_editor):
    """Map old 4-value roles to new 2-value system.
    owner  -> org_admin
    admin  -> org_admin
    manager -> member
    member  -> member
    """
    OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
    OrganizationMember.objects.filter(role__in=['owner', 'admin']).update(role='org_admin')
    OrganizationMember.objects.filter(role__in=['manager', 'member']).update(role='member')


def migrate_org_member_roles_backward(apps, schema_editor):
    OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
    OrganizationMember.objects.filter(role='org_admin').update(role='admin')


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0004_alter_organizationmember_role'),
    ]

    operations = [
        migrations.RunPython(
            migrate_org_member_roles_forward,
            reverse_code=migrate_org_member_roles_backward,
        ),
        migrations.AlterField(
            model_name='organizationmember',
            name='role',
            field=models.CharField(
                choices=[
                    ('org_admin', 'Organization Admin'),
                    ('member', 'Member'),
                ],
                default='member',
                max_length=20,
            ),
        ),
    ]

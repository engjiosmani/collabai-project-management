from django.db import migrations

_JOB_ROLES = [
    ('backend_developer', 'Backend Developer', 'APIs, business logic, DRF, auth.', ['backend', 'api', 'auth', 'middleware', 'async', 'cache', 'multi-tenancy']),
    ('frontend_developer', 'Frontend Developer', 'React UI, Context API.', ['frontend']),
    ('full_stack_developer', 'Full Stack Developer', 'End-to-end features.', ['backend', 'frontend', 'api', 'auth']),
    ('devops_engineer', 'DevOps Engineer', 'CI/CD, deployment.', ['ci', 'testing']),
    ('qa_engineer', 'QA / Test Engineer', 'Automated and E2E tests.', ['testing']),
    ('tech_lead', 'Tech Lead / Architect', 'Architecture and alignment.', ['architecture', 'project-management']),
    ('data_engineer', 'Data Engineer', 'Database and ORM.', ['db']),
    ('security_engineer', 'Security Engineer', 'Auth hardening and reviews.', ['security', 'auth']),
    ('ai_engineer', 'AI / ML Engineer', 'LLM and AI features.', ['ai']),
    ('mobile_developer', 'Mobile Developer', 'Mobile clients.', ['frontend']),
    ('ui_ux_designer', 'UI/UX Designer', 'Design and usability.', ['frontend', 'docs']),
    ('product_manager', 'Product Manager', 'Roadmap and requirements.', ['project-management', 'docs']),
    ('technical_writer', 'Technical Writer', 'Documentation.', ['docs']),
]


def seed_job_roles(apps, schema_editor):
    JobRole = apps.get_model('workspaces', 'JobRole')

    for code, name, description, categories in _JOB_ROLES:
        JobRole.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
                'task_categories': categories,
                'is_active': True,
            },
        )


def unseed_job_roles(apps, schema_editor):
    JobRole = apps.get_model('workspaces', 'JobRole')
    codes = [row[0] for row in _JOB_ROLES]
    JobRole.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0004_jobrole_teammember_job_role'),
    ]

    operations = [
        migrations.RunPython(seed_job_roles, unseed_job_roles),
    ]

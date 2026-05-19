"""Default company job roles seeded into the database."""

DEFAULT_JOB_ROLES = [
    {
        'code': 'backend_developer',
        'name': 'Backend Developer',
        'description': 'APIs, business logic, DRF, auth, database integration.',
        'task_categories': ['backend', 'api', 'auth', 'middleware', 'async', 'cache', 'multi-tenancy'],
    },
    {
        'code': 'frontend_developer',
        'name': 'Frontend Developer',
        'description': 'React UI, Context API, client-side state and UX.',
        'task_categories': ['frontend'],
    },
    {
        'code': 'full_stack_developer',
        'name': 'Full Stack Developer',
        'description': 'End-to-end features across backend and frontend.',
        'task_categories': ['backend', 'frontend', 'api', 'auth'],
    },
    {
        'code': 'devops_engineer',
        'name': 'DevOps Engineer',
        'description': 'CI/CD, deployment, infrastructure, monitoring.',
        'task_categories': ['ci', 'testing'],
    },
    {
        'code': 'qa_engineer',
        'name': 'QA / Test Engineer',
        'description': 'Automated tests, E2E, quality gates.',
        'task_categories': ['testing'],
    },
    {
        'code': 'tech_lead',
        'name': 'Tech Lead / Architect',
        'description': 'Architecture, technical decisions, cross-team alignment.',
        'task_categories': ['architecture', 'project-management'],
    },
    {
        'code': 'data_engineer',
        'name': 'Data Engineer',
        'description': 'Database design, ORM models, migrations, data layer.',
        'task_categories': ['db'],
    },
    {
        'code': 'security_engineer',
        'name': 'Security Engineer',
        'description': 'Auth hardening, security reviews, compliance.',
        'task_categories': ['security', 'auth'],
    },
    {
        'code': 'ai_engineer',
        'name': 'AI / ML Engineer',
        'description': 'LLM integration, embeddings, AI features.',
        'task_categories': ['ai'],
    },
    {
        'code': 'mobile_developer',
        'name': 'Mobile Developer',
        'description': 'iOS/Android or cross-platform mobile clients.',
        'task_categories': ['frontend'],
    },
    {
        'code': 'ui_ux_designer',
        'name': 'UI/UX Designer',
        'description': 'Design systems, wireframes, usability.',
        'task_categories': ['frontend', 'docs'],
    },
    {
        'code': 'product_manager',
        'name': 'Product Manager',
        'description': 'Roadmap, requirements, stakeholder communication.',
        'task_categories': ['project-management', 'docs'],
    },
    {
        'code': 'technical_writer',
        'name': 'Technical Writer',
        'description': 'Documentation, API guides, READMEs.',
        'task_categories': ['docs'],
    },
]

# Distributed Systems 2025/26 - Requirements Checklist

This file maps each course requirement to the current CollabAI implementation.

## Summary

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Client-server architecture | Done | React SPA in `frontend/`; Django API in `backend/`; communication through `frontend/src/api/api.js` and `/api/v1/`. |
| 2 | HTTP/HTTPS REST communication | Done | REST endpoints under `/api/v1/`; Axios client uses HTTP locally; production HTTPS controls are environment-driven in `backend/config/settings.py`. |
| 3 | Minimum 20 endpoints | Done | `backend/schema.yml` currently contains 63 API paths. See `docs/api-endpoints.md`. |
| 4 | RESTful API and framework | Done | Django REST Framework, `APIView`, `ModelViewSet`, serializers, permissions, and `django-filter`. |
| 5 | OOP | Done | Class-based models, serializers, views, services, permissions, middleware; models inherit `common.models.BaseModel`. |
| 6 | Swagger documentation | Done | Swagger UI: `/api/docs/`; OpenAPI schema: `/api/schema/`; implemented with `drf-spectacular`. |
| 7 | ORM and database | Done | Django ORM models across domain apps; PostgreSQL for normal runtime; migrations under each app. |
| 8 | Authentication and authorization | Done | JWT register/login/refresh/logout; role-based authorization through organization and workspace roles. |
| 9 | Middleware | Done | Request logging, JWT enforcement, CORS, and tenant middleware are registered in `settings.MIDDLEWARE`. |
| 10 | Frontend React + Context | Done | React app with `AuthContext`, `OrganizationContext`, `NotificationContext`, and `DashboardContext`. |
| 11 | Tests + CI/CD | Done | Backend unit/API tests, frontend Jest tests, Cypress E2E, and GitHub Actions workflows. |
| 12 | Minimum 20 models + migrations | Done | 24 project models and 44 app migration files. See `docs/database-models.md`. |
| 13 | Project documentation | Done | Architecture, backend architecture, setup, API, database, security, AI, and caching docs in `docs/`. |
| 14 | Project management | External proof needed | Use GitHub Projects, Jira, or screenshots/links for the final submission. Not provable from source code alone. |
| 15 | Git and collaboration | Partially verifiable | GitHub remote and commits exist. PRs/code reviews need GitHub screenshots or links for submission proof. |
| 16 | LLM integration | Partially done | AI module is implemented with Groq (`apps.ai_assistant`), not OpenAI. If OpenAI is strictly required, add an OpenAI client/provider. |
| 17 | Caching | Done | Redis/django-redis caching with LocMem fallback; cached list/dashboard endpoints; cache invalidation signals. |
| 18 | Async tasks/background jobs | Done | Celery configured; AI reindexing and email-related tasks use background jobs. |
| 19 | Multi-tenancy architecture | Done | Organization-scoped tenants with `X-Organization-ID`, tenant middleware, tenant query helpers, and organization memberships. |
| 20 | Search and filtering | Done | DRF SearchFilter, OrderingFilter, django-filter FilterSets for projects, tasks, workspaces, comments, notifications, users, audit logs. |

## Notes for final submission

- Requirement #16 is the main technical mismatch: the implemented external LLM provider is Groq. The code satisfies chatbot/text-analysis behavior, but not the exact "OpenAI API" wording.
- Requirements #14 and #15 require external evidence, usually screenshots or links from GitHub Projects/Jira, pull requests, and code reviews.
- The current API schema should be regenerated after route changes with:

```bash
cd backend
python manage.py spectacular --file schema.yml
```

## Key files

| Area | Files |
|------|-------|
| API routing | `backend/config/urls.py`, `backend/config/api_v1_urls.py`, app `urls.py` files |
| Swagger/OpenAPI | `backend/config/urls.py`, `backend/common/openapi.py`, `backend/schema.yml` |
| Auth/RBAC | `backend/apps/core/views/api.py`, `backend/config/middleware.py`, `backend/common/role_permissions.py` |
| Tenancy | `backend/apps/core/middleware.py`, `backend/common/tenant_access.py`, `backend/common/tenant_queryset.py`, `backend/common/tenant_viewset.py` |
| Caching | `backend/common/cache.py`, `backend/common/cache_signals.py`, app `signals.py` files |
| Background jobs | `backend/config/celery.py`, `backend/apps/ai_assistant/tasks.py`, `backend/apps/core/tasks.py` |
| AI | `backend/apps/ai_assistant/` |
| Frontend context | `frontend/src/context/` |
| CI/CD | `.github/workflows/` |

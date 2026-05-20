# API endpoints

**Canonical rule:** all product REST endpoints use prefix **`/api/v1`**. Document tooling lives at **`/api/docs/`** and **`/api/schema/`** (no version segment). GitHub Issues must copy paths from this file to avoid drift.

Base URL (development): `http://127.0.0.1:8000/api/v1`

Swagger UI: `http://127.0.0.1:8000/api/docs/`  
OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

## Authentication

### Register user

| Item | Value |
|------|--------|
| Story | AUTH-01 |
| Method | `POST` |
| Path | `/auth/register` |
| Full URL | `/api/v1/auth/register` |

### Login (JWT)

| Item | Value |
|------|--------|
| Story | AUTH-02 |
| Method | `POST` |
| Path | `/auth/login` |
| Full URL | `/api/v1/auth/login` |

### Refresh token (JWT)

| Item | Value |
|------|--------|
| Story | AUTH-02 |
| Method | `POST` |
| Path | `/auth/refresh` |
| Full URL | `/api/v1/auth/refresh` |

### Logout (JWT)

| Item | Value |
|------|--------|
| Story | AUTH-02 |
| Method | `POST` |
| Path | `/auth/logout` |
| Full URL | `/api/v1/auth/logout` |

**Request body (JSON)**

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

**Success:** `201 Created`

Response body includes `id` and `email`. Password is write-only and never returned.

**Validation errors:** `400 Bad Request`

Typical payload shape:

```json
{
  "email": ["A user with this email already exists."]
}
```

or

```json
{
  "password": ["Password must contain at least one uppercase letter."]
}
```

Password rules combine Django validators plus extra complexity checks (mixed case, digit, special character).

## AI / LLM module

Story: **#16** — external LLM (Groq) via `apps.ai_assistant`. See [ai-module.md](./ai-module.md).

All paths require `Authorization: Bearer <access_token>` unless noted.

### Text analysis

| Item | Value |
|------|--------|
| Method | `POST` |
| Full URL | `/api/v1/ai/analyze/` |
| Swagger tag | `AI / Text analysis` |

**Request body**

```json
{
  "text": "Meeting notes or any plain text (max 16000 chars).",
  "mode": "summary",
  "task_id": null
}
```

`mode`: `summary` | `action_items` | `sentiment`

**Success:** `200 OK`

```json
{
  "mode": "summary",
  "result": "… LLM output …",
  "request_id": 42
}
```

**Errors:** `400` validation, `503` missing/invalid `GROQ_API_KEY` or LLM failure

### RAG chatbot (workspace Q&A)

| Item | Value |
|------|--------|
| Method | `POST` |
| Full URL | `/api/v1/ai/query/` |
| Swagger tag | `AI / RAG` |

**Request body**

```json
{
  "workspace_id": 1,
  "question": "What is the status of JWT auth?",
  "top_k": 5,
  "task_id": null
}
```

**Success:** `200 OK` — `answer`, `sources`, `request_id`

### Semantic search (no LLM)

| Method | Full URL |
|--------|----------|
| `POST` | `/api/v1/ai/search/` |

Body: `workspace_id`, `query`, optional `top_k`.

### Reindex workspace vectors

| Method | Full URL |
|--------|----------|
| `POST` | `/api/v1/ai/reindex/` |

Body: `workspace_id`. **Success:** `202 Accepted` with Celery `task_id`.

### AI request history

| Method | Full URL |
|--------|----------|
| `GET` | `/api/v1/ai/history/` |

Returns last 50 `AIRequest` rows for the authenticated user.

### LLM config (diagnostics)

| Method | Full URL |
|--------|----------|
| `GET` | `/api/v1/ai/config/` |

Returns `groq_configured`, `groq_model`, optional `hint`.

### Task generator

| Method | Full URL |
|--------|----------|
| `POST` | `/api/v1/ai/task-generator/plans/` |
| `GET` | `/api/v1/ai/task-generator/plans/<id>/` |
| `GET` | `/api/v1/ai/task-generator/plans/<id>/status/` |
| `POST` | `/api/v1/ai/task-generator/plans/<id>/approve/` |
| `POST` | `/api/v1/ai/task-generator/plans/<id>/reject/` |
| … | See Swagger `AI / Task Generator` |

### Team Pulse

| Method | Full URL |
|--------|----------|
| `GET` | `/api/v1/ai/team-pulse/?workspace_id=1` |
| `PUT` | `/api/v1/ai/team-pulse/github/` |
| `POST` | `/api/v1/ai/team-pulse/run/` |

See Swagger tags `AI / Team Pulse`.

## Verified endpoints (extracted from OpenAPI schema on 2026-05-20)

Summary: the running backend exposes 57 OpenAPI paths and 91 HTTP operations (GET/POST/PUT/PATCH/DELETE).

checklist of the documented REST operations (path — method — tag — summary when available).

- GET `/api/schema/` — schema
- GET `/api/v1/activity-logs/` — Activity logs — List activity logs
- GET `/api/v1/activity-logs/{id}/` — Activity logs — Retrieve activity log
- POST `/api/v1/ai/analyze/` — AI / Text analysis
- POST `/api/v1/ai/chatbot/` — AI / ChatBot
- GET `/api/v1/ai/config/` — AI / Task Generator
- GET `/api/v1/ai/history/` — AI / RAG
- POST `/api/v1/ai/query/` — AI / RAG
- POST `/api/v1/ai/reindex/` — AI / RAG
- POST `/api/v1/ai/search/` — AI / RAG
- POST `/api/v1/ai/task-generator/plans/` — AI / Task Generator
- GET `/api/v1/ai/task-generator/plans/{plan_id}/` — AI / Task Generator
- POST `/api/v1/ai/task-generator/plans/{plan_id}/approve/` — AI / Task Generator
- GET `/api/v1/ai/task-generator/plans/{plan_id}/preview-markdown/` — AI / Task Generator
- DELETE `/api/v1/ai/task-generator/plans/{plan_id}/reject/` — AI / Task Generator
- GET `/api/v1/ai/task-generator/plans/{plan_id}/status/` — AI / Task Generator
- PATCH `/api/v1/ai/task-generator/plans/{plan_id}/tasks/{task_id}/` — AI / Task Generator
- POST `/api/v1/ai/task-generator/plans/{plan_id}/tasks/{task_id}/regenerate/` — AI / Task Generator
- GET `/api/v1/ai/team-pulse/` — AI / Team Pulse
- GET `/api/v1/ai/team-pulse/github/` — AI / Team Pulse
- PUT `/api/v1/ai/team-pulse/github/` — AI / Team Pulse
- POST `/api/v1/ai/team-pulse/run/` — AI / Team Pulse
- GET `/api/v1/audit/` — Audit logs — List audit logs
- GET `/api/v1/audit/{id}/` — Audit logs — Retrieve audit log
- POST `/api/v1/auth/login` — Authentication
- POST `/api/v1/auth/logout` — Authentication
- POST `/api/v1/auth/refresh` — Authentication
- POST `/api/v1/auth/register` — Authentication
- GET `/api/v1/comments/` — Comments — List comments
- POST `/api/v1/comments/` — Comments — Create comment
- GET `/api/v1/comments/{id}/` — Comments — Retrieve comment
- PUT `/api/v1/comments/{id}/` — Comments — Update comment
- PATCH `/api/v1/comments/{id}/` — Comments — Partially update comment
- DELETE `/api/v1/comments/{id}/` — Comments — Delete comment
- GET `/api/v1/dashboard/summary/` — Dashboard
- GET `/api/v1/health/` — Operations
- GET `/api/v1/invites/` — Invites — List workspace invites
- POST `/api/v1/invites/` — Invites — Create workspace invite
- GET `/api/v1/invites/{id}/` — Invites — Retrieve workspace invite
- PUT `/api/v1/invites/{id}/` — Invites — Update workspace invite
- PATCH `/api/v1/invites/{id}/` — Invites — Partially update workspace invite
- DELETE `/api/v1/invites/{id}/` — Invites — Delete workspace invite
- POST `/api/v1/invites/{id}/accept/` — Invites — Accept a workspace invite
- GET `/api/v1/job-roles/` — Job roles — List job roles for task assignment
- GET `/api/v1/job-roles/{id}/` — Job roles — Retrieve job role
- GET `/api/v1/metrics/` — Operations
- GET `/api/v1/notifications/` — Notifications — List notifications
- POST `/api/v1/notifications/` — Notifications — Create notification
- GET `/api/v1/notifications/{id}/` — Notifications — Retrieve notification
- PUT `/api/v1/notifications/{id}/` — Notifications — Update notification
- PATCH `/api/v1/notifications/{id}/` — Notifications — Partially update notification
- DELETE `/api/v1/notifications/{id}/` — Notifications — Delete notification
- POST `/api/v1/notifications/{id}/mark_read/` — Notifications — Mark notification as read
- POST `/api/v1/notifications/mark_all_read/` — Notifications — Mark all notifications as read
- GET `/api/v1/organizations/` — Organizations — List organizations
- POST `/api/v1/organizations/` — Organizations — Create organization
- GET `/api/v1/organizations/{id}/` — Organizations — Retrieve organization
- PUT `/api/v1/organizations/{id}/` — Organizations — Update organization
- PATCH `/api/v1/organizations/{id}/` — Organizations — Partially update organization
- DELETE `/api/v1/organizations/{id}/` — Organizations — Delete organization
- GET `/api/v1/organizations/{id}/members/` — Organizations — List organization members
- PATCH `/api/v1/organizations/{id}/members/{member_id}/job-role/` — Organizations — Set a member job role
- GET `/api/v1/permissions/` — Permissions — List permissions
- POST `/api/v1/permissions/` — Permissions — Create permission
- GET `/api/v1/permissions/{id}/` — Permissions — Retrieve permission
- PUT `/api/v1/permissions/{id}/` — Permissions — Update permission
- PATCH `/api/v1/permissions/{id}/` — Permissions — Partially update permission
- DELETE `/api/v1/permissions/{id}/` — Permissions — Delete permission
- GET `/api/v1/projects/` — Projects — List projects
- POST `/api/v1/projects/` — Projects — Create project
- GET `/api/v1/projects/{id}/` — Projects — Retrieve project
- PUT `/api/v1/projects/{id}/` — Projects — Update project
- PATCH `/api/v1/projects/{id}/` — Projects — Partially update project
- DELETE `/api/v1/projects/{id}/` — Projects — Delete project
- GET `/api/v1/roles/` — Roles — List roles
- POST `/api/v1/roles/` — Roles — Create role
- GET `/api/v1/roles/{id}/` — Roles — Retrieve role
- PUT `/api/v1/roles/{id}/` — Roles — Update role
- PATCH `/api/v1/roles/{id}/` — Roles — Partially update role
- DELETE `/api/v1/roles/{id}/` — Roles — Delete role
- GET `/api/v1/task-statuses/` — Task statuses — List task statuses
- GET `/api/v1/tasks/` — Tasks — List tasks
- POST `/api/v1/tasks/` — Tasks — Create task
- GET `/api/v1/tasks/{id}/` — Tasks — Retrieve task
- PUT `/api/v1/tasks/{id}/` — Tasks — Update task
- PATCH `/api/v1/tasks/{id}/` — Tasks — Partially update task
- DELETE `/api/v1/tasks/{id}/` — Tasks — Delete task
- GET `/api/v1/users/` — Users — List users
- GET `/api/v1/users/{id}/` — Users — Retrieve user
- GET `/api/v1/users/me/` — Users — Get or update the current user
- PATCH `/api/v1/users/me/` — Users — Get or update the current user



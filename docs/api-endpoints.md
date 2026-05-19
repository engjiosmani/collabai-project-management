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

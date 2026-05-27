# CollabAI API Endpoints

All product endpoints use the `/api/v1/` prefix. Documentation tooling is outside the versioned API.

| Item | URL |
|------|-----|
| Development API base | `http://127.0.0.1:8000/api/v1` |
| Swagger UI | `http://127.0.0.1:8000/api/docs/` |
| OpenAPI schema | `http://127.0.0.1:8000/api/schema/` |

Authentication uses JWT Bearer tokens:

```http
Authorization: Bearer <access-token>
```

Tenant-scoped requests can select the active organization with:

```http
X-Organization-ID: <organization-id>
```

## Authentication

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `POST` | `/api/v1/auth/register` | Register a user | Public |
| `POST` | `/api/v1/auth/login` | Login and receive JWT tokens | Public |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | Public |
| `POST` | `/api/v1/auth/logout` | Blacklist refresh token | JWT |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset email | Public |
| `POST` | `/api/v1/auth/reset-password` | Reset password with token | Public |

## Core and Operations

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/health/` | Health check for database, cache, vector store, and LLM configuration |
| `GET` | `/api/v1/metrics/` | Admin-only platform metrics |
| `GET` | `/api/v1/dashboard/summary/` | Tenant-scoped dashboard summary |
| `GET` | `/api/schema/` | OpenAPI schema |
| `GET` | `/api/docs/` | Swagger UI |

## Organizations and Invitations

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/organizations/` | List organizations visible to current user |
| `POST` | `/api/v1/organizations/` | Create organization |
| `GET` | `/api/v1/organizations/{id}/` | Retrieve organization |
| `PUT` | `/api/v1/organizations/{id}/` | Replace organization |
| `PATCH` | `/api/v1/organizations/{id}/` | Update organization |
| `DELETE` | `/api/v1/organizations/{id}/` | Delete organization |
| `GET` | `/api/v1/organizations/{id}/members/` | List organization members |
| `GET` | `/api/v1/organizations/{id}/members/{user_id}/` | Retrieve organization member |
| `PATCH` | `/api/v1/organizations/{id}/members/{user_id}/` | Update member role |
| `DELETE` | `/api/v1/organizations/{id}/members/{user_id}/` | Remove member |
| `PATCH` | `/api/v1/organizations/{id}/members/{member_id}/job-role/` | Set organization member job role |
| `POST` | `/api/v1/organizations/{id}/invite/` | Invite user to organization/workspace |
| `GET` | `/api/v1/organizations/{id}/invites/` | List organization invites |
| `DELETE` | `/api/v1/organizations/{id}/invites/{invite_id}/` | Revoke invite |
| `GET` | `/api/v1/invites/my/` | List invites for current user |
| `POST` | `/api/v1/invites/{token}/accept/` | Accept invite token |

## Workspaces and Job Roles

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/workspaces/` | List accessible workspaces |
| `POST` | `/api/v1/workspaces/` | Create workspace |
| `GET` | `/api/v1/workspaces/{id}/` | Retrieve workspace |
| `PUT` | `/api/v1/workspaces/{id}/` | Replace workspace |
| `PATCH` | `/api/v1/workspaces/{id}/` | Update workspace |
| `DELETE` | `/api/v1/workspaces/{id}/` | Delete workspace |
| `GET` | `/api/v1/workspaces/{id}/members/` | List workspace members |
| `PATCH` | `/api/v1/workspaces/{id}/members/{member_id}/job-role/` | Set workspace member job role |
| `GET` | `/api/v1/job-roles/` | List job roles |
| `GET` | `/api/v1/job-roles/{id}/` | Retrieve job role |
| `GET` | `/api/v1/organizations/{id}/workspaces/` | List workspaces inside organization |
| `POST` | `/api/v1/organizations/{id}/workspaces/` | Create workspace inside organization |
| `GET` | `/api/v1/organizations/{id}/workspaces/{ws_id}/` | Retrieve organization workspace |
| `PUT` | `/api/v1/organizations/{id}/workspaces/{ws_id}/` | Replace organization workspace |
| `PATCH` | `/api/v1/organizations/{id}/workspaces/{ws_id}/` | Update organization workspace |
| `DELETE` | `/api/v1/organizations/{id}/workspaces/{ws_id}/` | Delete organization workspace |
| `GET` | `/api/v1/organizations/{id}/workspaces/{ws_id}/members/` | List workspace members |
| `POST` | `/api/v1/organizations/{id}/workspaces/{ws_id}/members/` | Add workspace member |
| `PATCH` | `/api/v1/organizations/{id}/workspaces/{ws_id}/members/{user_id}/` | Update workspace member role |
| `DELETE` | `/api/v1/organizations/{id}/workspaces/{ws_id}/members/{user_id}/` | Remove workspace member |

## Projects

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/projects/` | List visible projects |
| `POST` | `/api/v1/projects/` | Create project |
| `GET` | `/api/v1/projects/{id}/` | Retrieve project |
| `PUT` | `/api/v1/projects/{id}/` | Replace project |
| `PATCH` | `/api/v1/projects/{id}/` | Update project |
| `DELETE` | `/api/v1/projects/{id}/` | Delete project |
| `GET` | `/api/v1/projects/{id}/members/` | List project members |
| `POST` | `/api/v1/projects/{id}/members/` | Add project member |
| `GET` | `/api/v1/projects/{id}/members/{user_id}/` | Retrieve project member |
| `DELETE` | `/api/v1/projects/{id}/members/{user_id}/` | Remove project member |

## Tasks

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/tasks/` | List visible tasks |
| `POST` | `/api/v1/tasks/` | Create task |
| `GET` | `/api/v1/tasks/{id}/` | Retrieve task |
| `PUT` | `/api/v1/tasks/{id}/` | Replace task |
| `PATCH` | `/api/v1/tasks/{id}/` | Update task |
| `DELETE` | `/api/v1/tasks/{id}/` | Delete task |
| `GET` | `/api/v1/task-statuses/` | List task status catalog |
| `GET` | `/api/v1/task-priorities/` | List task priority catalog |
| `GET` | `/api/v1/tasks/{id}/attachments/` | List task attachments |
| `POST` | `/api/v1/tasks/{id}/attachments/` | Upload attachment |
| `DELETE` | `/api/v1/tasks/{id}/attachments/{attachment_id}/` | Delete attachment |
| `GET` | `/api/v1/tasks/{id}/attachments/{attachment_id}/download/` | Download attachment |

## Comments and Activity

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/comments/` | List comments |
| `POST` | `/api/v1/comments/` | Create comment |
| `GET` | `/api/v1/comments/{id}/` | Retrieve comment |
| `PUT` | `/api/v1/comments/{id}/` | Replace comment |
| `PATCH` | `/api/v1/comments/{id}/` | Update comment |
| `DELETE` | `/api/v1/comments/{id}/` | Delete comment |
| `GET` | `/api/v1/activity-logs/` | List activity logs |
| `GET` | `/api/v1/activity-logs/{id}/` | Retrieve activity log |

## Notifications

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/notifications/` | List notifications |
| `POST` | `/api/v1/notifications/` | Create notification |
| `GET` | `/api/v1/notifications/{id}/` | Retrieve notification |
| `PUT` | `/api/v1/notifications/{id}/` | Replace notification |
| `PATCH` | `/api/v1/notifications/{id}/` | Update notification |
| `DELETE` | `/api/v1/notifications/{id}/` | Delete notification |
| `POST` | `/api/v1/notifications/{id}/mark_read/` | Mark one notification read |
| `POST` | `/api/v1/notifications/mark_all_read/` | Mark all notifications read |

## Users and Profile

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/users/` | List users |
| `GET` | `/api/v1/users/{id}/` | Retrieve user |
| `GET` | `/api/v1/users/me/` | Retrieve current user |
| `PATCH` | `/api/v1/users/me/` | Update current user |
| `GET` | `/api/v1/profile/` | Retrieve profile |
| `PUT` | `/api/v1/profile/` | Replace profile |
| `PATCH` | `/api/v1/profile/` | Update profile |
| `POST` | `/api/v1/profile/change-password/` | Change password |
| `GET` | `/api/v1/profile/memberships/` | List current user's organization/workspace memberships |

## AI Assistant

The AI assistant currently uses Groq as the external LLM provider.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/ai/chatbot/` | General chatbot response |
| `POST` | `/api/v1/ai/analyze/` | Text analysis: summary, action items, sentiment |
| `POST` | `/api/v1/ai/search/` | Semantic search without LLM answer generation |
| `POST` | `/api/v1/ai/query/` | RAG question answering with organization context |
| `POST` | `/api/v1/ai/reindex/` | Queue organization reindex background job |
| `GET` | `/api/v1/ai/history/` | List recent AI request history |

## Audit

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/audit/` | List audit logs |
| `GET` | `/api/v1/audit/{id}/` | Retrieve audit log |

## Search, filtering, ordering, and pagination

The API enables DRF's `SearchFilter`, `OrderingFilter`, and `django-filter` globally. Common query parameters:

| Parameter | Purpose |
|-----------|---------|
| `search` | Full-text-like search across configured `search_fields`. |
| `ordering` | Sort by configured `ordering_fields`; prefix with `-` for descending. |
| `page` | Page number. |
| `page_size` | Page size, limited by `common.pagination.StandardPagination`. |

Examples:

```http
GET /api/v1/tasks/?search=frontend&status=in_progress&priority=high&ordering=-due_date
GET /api/v1/projects/?organization=1&workspace=2&search=api
GET /api/v1/notifications/?is_read=false&ordering=-created_at
```

## Regenerating the schema

After route or serializer changes, regenerate the schema:

```bash
cd backend
python manage.py spectacular --file schema.yml
```

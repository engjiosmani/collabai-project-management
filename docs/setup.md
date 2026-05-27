# CollabAI Local Setup

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL
- Redis Stack for caching, Celery broker/backend, and optional vector search for RAG

## Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Required for every backend start. Generate one with Django's `get_random_secret_key`. |
| `DEBUG` | `True` locally; `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated host allowlist. |
| `DB_HOST` | PostgreSQL host. |
| `DB_PORT` | PostgreSQL port. |
| `DB_NAME` | PostgreSQL database name. |
| `DB_USER` | PostgreSQL user. |
| `DB_PASSWORD` | PostgreSQL password. |
| `REDIS_URL` | Redis cache URL, for example `redis://127.0.0.1:6379/0`. |
| `CACHE_DEFAULT_TIMEOUT` | Cache TTL in seconds. |
| `CELERY_BROKER_URL` | Celery broker URL, usually Redis. |
| `CELERY_RESULT_BACKEND` | Celery result backend URL. |
| `CELERY_TASK_ALWAYS_EAGER` | Use `true` for simple local debugging; use `false` with a worker for real async behavior. |
| `GROQ_API_KEY` | LLM API key for chatbot, text analysis, and RAG answers. |
| `GROQ_MODEL` | LLM model name. |
| `RAG_EMBEDDING_MODEL` | Embedding model used for semantic search/RAG. |
| `FRONTEND_URL` | Frontend URL used in links such as password reset. |

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

Swagger UI:

```text
http://127.0.0.1:8000/api/docs/
```

OpenAPI schema:

```text
http://127.0.0.1:8000/api/schema/
```

## Backend checks

Verify Django configuration:

```bash
python manage.py check
```

Verify Groq configuration:

```bash
python manage.py check_groq
```

Verify Redis:

```bash
python manage.py check_redis
```

If Redis is not running locally, remove or comment out `REDIS_URL` for development. Django will use LocMem cache, but Redis should be used for the course caching demo.

On Windows, Hyper-V can reserve port `6379`. If Docker cannot publish Redis on that port, use another host port such as `16379` and set:

```text
REDIS_URL=redis://127.0.0.1:16379/0
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Set the API URL in `frontend/.env`:

```text
REACT_APP_API_URL=http://127.0.0.1:8000/api/v1
```

Start the frontend:

```bash
npm start
```

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

The compose stack includes PostgreSQL, Redis Stack, Django backend, and React frontend.

## Optional Celery worker

Use this when `CELERY_TASK_ALWAYS_EAGER=false`:

```bash
cd backend
celery -A config worker -l info
```

Optional beat process:

```bash
cd backend
celery -A config beat -l info
```

## Tests

Backend:

```bash
cd backend
python manage.py test
```

Frontend:

```bash
cd frontend
npm test -- --watchAll=false
```

Cypress E2E:

```bash
cd frontend
npm run e2e:ci
```

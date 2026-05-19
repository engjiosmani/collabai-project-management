# CollabAI — Local setup

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL
- Redis Stack (cache, Celery broker, optional vector search for RAG)

## Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | LLM API key from [console.groq.com](https://console.groq.com) (chatbot, text analysis, task generator, team pulse) |
| `GROQ_MODEL` | Default model (e.g. `llama-3.1-8b-instant`) |
| `REDIS_URL` | **Required for production caching** — list/dashboard cache + vector store |
| `CACHE_DEFAULT_TIMEOUT` | List/dashboard TTL in seconds (default `300`) |
| `CELERY_BROKER_URL` | Background jobs (reindex, standup, plan generation) |

Verify Groq connectivity:

```bash
python manage.py check_groq
```

Verify Redis (required for caching demo / requirement #17):

```bash
python manage.py check_redis
```

Start Redis Stack locally, then set `REDIS_URL=redis://127.0.0.1:6379/0` in `backend/.env`.

Run migrations and server:

```bash
python manage.py migrate
python manage.py runserver
```

Swagger: `http://127.0.0.1:8000/api/docs/`

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Set `REACT_APP_API_URL=http://127.0.0.1:8000/api/v1` in `frontend/.env`, then:

```bash
npm start
```

## Optional: Celery worker

```bash
cd backend
celery -A config worker -l info
celery -A config beat -l info
```

Set `CELERY_TASK_ALWAYS_EAGER=false` in `.env` when running workers for real async behavior.

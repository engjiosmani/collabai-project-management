# Backend Security and Authentication Configuration

This document outlines the security architecture, hardening policies, and environment configurations implemented in the CollabAI backend to secure API requests, protect user credentials, and manage state safely.

---

## 1. Secrets & Environment Configuration

All sensitive settings and environment-specific parameters are decoupled from the source code and managed via standard environment variables loaded from a `.env` file at the root of the backend directory.

### Core Environment Variables

| Variable | Description | Default / Development Value | Enforcement / Policy |
| :--- | :--- | :--- | :--- |
| `DEBUG` | Enables/disables verbose Django debug/error screens. | `True` | **Must** be set to `False` in production. |
| `SECRET_KEY` | The secret key used to provide cryptographic signing. | (Django dev default) | **Enforced**: Will raise `ImproperlyConfigured` on startup in production if missing. |
| `DB_PASSWORD` | PostgreSQL database user credential password. | `12345678` | **Enforced**: Will raise `ImproperlyConfigured` on startup in production if missing or default. |
| `ALLOWED_HOSTS` | Comma-separated list of host names authorized to serve the API. | `localhost,127.0.0.1,testserver` | Filters incoming headers against host header attacks. |

> [!CAUTION]
> **Secret Key Rotation Warning**: The `SECRET_KEY` placeholder provided in `.env.example` is strictly for local development and testing. In a staging or production deployment, you **must** generate a unique, high-entropy secret key and set it via the `SECRET_KEY` environment variable. Never commit the production secret key or reuse the example value.

---

## 2. CORS & CSRF Controls

Cross-Origin Resource Sharing (CORS) and Cross-Site Request Forgery (CSRF) protections are configured to allow communication only with authorized frontend services.

### CORS Configuration
- **All Origins (`CORS_ALLOW_ALL_ORIGINS`)**: Controlled by environment variable. Defaults to `True` when `DEBUG=True`. Must be `False` in production.
- **Allowed Origins (`CORS_ALLOWED_ORIGINS`)**: Defined as a comma-separated list of origins (e.g. `http://localhost:3000,http://127.0.0.1:3000`).
- **Allowed Methods & Headers**: Restricts preflight requests only to expected methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`) and safe headers (`authorization`, `content-type`, `x-request-id`, etc.).

### CSRF Protection
- **Trusted Origins (`CSRF_TRUSTED_ORIGINS`)**: Defined as a comma-separated list of origins trusted to submit state-changing POST/PUT/PATCH/DELETE requests.
- **Parity with Frontend**: Synchronizes cookies and headers to prevent unauthorized cross-site actions on session endpoints.

---

## 3. JWT Authentication Policy

CollabAI employs stateless **JSON Web Tokens (JWT)** via `django-rest-framework-simplejwt` to handle authentication securely and responsively.

```
       +--------------+                    +---------------+
       |              |----[ Credentials ]>|               |
       |  Client App  |                    | Auth Service  |
       |              |<---[ Access JWT ]--|               |
       +--------------+                    +---------------+
              |
      [ Bearer Token Header ]
              |
              v
       +--------------+
       |  Protected   |
       |  API Route   |
       +--------------+
```

### Token Configuration
- **Access Tokens**: Short-lived access credentials. Valid for `60 minutes` by default (configurable via `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`).
- **Refresh Tokens**: Long-lived renewal credentials. Valid for `7 days` by default (configurable via `JWT_REFRESH_TOKEN_LIFETIME_DAYS`).
- **Token Rotation (`JWT_ROTATE_REFRESH_TOKENS`)**: Enabled by default (`True`). Each time a new access token is requested using a refresh token, a new refresh token is also issued.
- **Token Blacklisting (`JWT_BLACKLIST_AFTER_ROTATION`)**: Enabled by default (`True`). When refresh tokens are rotated, old refresh tokens are immediately blacklisted and cannot be reused, preventing replay attacks.
- **Header Parsing**: Parity is enforced using standard `Bearer` authorization headers: `Authorization: Bearer <JWT_TOKEN>`.

---

## 4. Password Strength & Brute-Force Rate Limiting (Throttling)

User registration and authentication enforce strict security requirements to protect against brute-force, credential stuffing, and dictionary-based dictionary attacks.

### Built-in Password Validators
The Django configuration includes the following default validators in `AUTH_PASSWORD_VALIDATORS`:
1. **UserAttributeSimilarityValidator**: Prevents passwords containing username, email, or other personal identifiers.
2. **MinimumLengthValidator**: Enforces a minimum password length (minimum of 8 characters).
3. **CommonPasswordValidator**: Rejects standard, commonly used, or easily guessable passwords.
4. **NumericPasswordValidator**: Disallows entirely numeric passwords (e.g. `12345678`).

### Custom Serializer Validation
During user registration in `RegisterSerializer`, additional regex validations are performed to ensure high-entropy passwords:
- At least one **uppercase letter** (`A-Z`).
- At least one **lowercase letter** (`a-z`).
- At least one **numeric digit** (`0-9`).
- At least one **special character** (e.g. `@`, `$`, `!`, `%`, `*`, `?`, `&`).

### API Rate Limiting (Throttling)
To prevent brute-force attacks on public endpoints (like `/api/v1/auth/login` and `/api/v1/auth/register`), DRF throttling is configured both globally and per endpoint:

**Global Throttles**
- **Anonymous Rate Limiting (`THROTTLE_ANON_RATE`)**: Enforces a default limit of `60 requests per minute` per IP address for unauthenticated requests.
- **Authenticated Rate Limiting (`THROTTLE_USER_RATE`)**: Enforces a default limit of `1000 requests per hour` for logged-in users.
- **Granular Scoped Authentication Rate Limiting**: Tighter per-endpoint restrictions are applied to critical auth paths to prevent brute-force, dictionary, and account enumeration attacks:
  - **Register Endpoint (`/api/v1/auth/register`)**: Restricted to `3 requests per minute` (configurable via `THROTTLE_AUTH_REGISTER_RATE`).
  - **Login Endpoint (`/api/v1/auth/login`)**: Restricted to `5 requests per minute` (configurable via `THROTTLE_AUTH_LOGIN_RATE`).
  - **Token Refresh Endpoint (`/api/v1/auth/refresh`)**: Restricted to `10 requests per minute` (configurable via `THROTTLE_AUTH_REFRESH_RATE`).
- All rates are completely environment-driven and can be adjusted for staging/production. Throttling is automatically bypassed during unit tests (`python manage.py test`) to prevent test suites from being blocked by shared cache states.

| Endpoint | Scope | Default Rate | Env Variable |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/login` | `auth_login` | `5/minute` | `THROTTLE_AUTH_LOGIN_RATE` |
| `POST /api/v1/auth/register` | `auth_register` | `3/minute` | `THROTTLE_AUTH_REGISTER_RATE` |

---

## 5. Production Hardening, Error & Logging Protections

To avoid exposing backend details and ensure safe deployments, special hardening measures are taken in production mode.

### Production Security Headers (SSL/HSTS)
When deploying under `DEBUG=False`, the following headers should be active to force encrypted HTTPS communication:
- **SSL Redirection (`SECURE_SSL_REDIRECT`)**: Re-routes all unencrypted HTTP traffic to HTTPS automatically.
- **HSTS Hardening (`SECURE_HSTS_SECONDS`)**: Instructs browsers to communicate only via HTTPS (recommended value: `31536000` seconds / 1 year).
- **Secure Cookies (`SESSION_COOKIE_SECURE` & `CSRF_COOKIE_SECURE`)**: Ensures that Django's session and CSRF cookies are strictly transmitted over secure HTTPS channels. These are environment-driven via `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` (set to `False` in local `.env` to support HTTP, but MUST be `True` in production).
- **Content-Type Sniffing (`SECURE_CONTENT_TYPE_NOSNIFF`)**: Prevents browsers from guessing/sniffing the MIME type of a response away from what is declared.
- **XSS Filter (`SECURE_BROWSER_XSS_FILTER`)**: Activates the browser's built-in Cross-Site Scripting filter.

### Celery Eager Mode Policy
- **Development (`CELERY_TASK_ALWAYS_EAGER=True`)**: Executes Celery tasks synchronously in the main thread to allow seamless debugging and zero Redis dependencies.
- **Production (`CELERY_TASK_ALWAYS_EAGER=False`)**: **Must** be set to `False` in production. This forces tasks to be offloaded asynchronously to the background worker pool, preventing API request threads from being blocked by heavy operations.

### Error Handling Policies
- **Development (`DEBUG=True`)**: Displays complete interactive tracebacks for exceptions and server errors to aid local troubleshooting.
- **Production (`DEBUG=False`)**: Supresses detailed tracebacks. Unexpected HTTP 500 errors are caught by our custom DRF exception handler (`common.exceptions.custom_exception_handler`), which logs the full traceback for backend administrators and returns a sanitized JSON error payload:
  ```json
  {
    "detail": "A server error occurred."
  }
  ```
- **X-Request-ID Parity**: Every request is assigned a unique UUID `X-Request-ID` attached to HTTP logs and responses. If an error occurs, the identifier is returned in the header to allow administrators to track the exception in backend logs without exposing technical details to clients.

---

## 6. Docker & Container Security Deployment

Both the backend and frontend are equipped with Docker containerization configurations to ensure standard, secure environment parity across staging and production deployments.

### Docker Configs
1. **Backend (`backend/Dockerfile`)**: Builds on top of `python:3.11-slim` using cached dependency layers and unbuffered output to optimize container size and diagnostic logs.
2. **Frontend (`frontend/Dockerfile`)**: Employs a multi-stage build. React is compiled inside a Node workspace, and the production-optimized bundle is served via a lightweight `nginx:stable-alpine` image to minimize vulnerability surface area.
3. **Orchestration (`docker-compose.yml`)**: Controls the database (PostgreSQL), memory store (Redis Stack), backend API, and React frontend inside isolated virtual networks.

### Instructions to Launch the Containerized Stack

1. **Populate Active Environment Configuration**:
   Ensure `backend/.env` is fully populated with production/staging configurations based on `backend/.env.example`.

2. **Launch with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```
   This builds the project, runs auto-migrations for the database, and exposes the services securely.

3. **Production Hardening Guidelines**:
   - **Environment Variables**: Never store absolute secret keys inside the `Dockerfile` or `docker-compose.yml`. Pass them strictly through the `.env` file or orchestrator secret manager.
   - **Port Exposure**: In production, do not expose port `5432` (PostgreSQL) or `6379` (Redis Stack) to the public interface. Let them communicate solely inside the private virtual network defined by Docker Compose.

---

## 7. Production Deployment Checklist

Before promoting any build to production, **every** variable below must be explicitly reviewed and updated in the active environment (`.env`, orchestrator secret manager, or platform settings). Defaults that are safe for local development are explicitly **unsafe** for production.

### Mandatory Changes

| Variable | Dev Value | Production Value | Why |
| :--- | :--- | :--- | :--- |
| `DEBUG` | `True` | `False` | Hides tracebacks; activates security-header defaults. |
| `SECRET_KEY` | Django dev key | **Unique, 50+ random chars** | Cryptographic signing key for sessions & JWT. Must never be reused across environments. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Your actual domain(s), e.g. `api.collabai.io` | Host-header attack mitigation. |
| `DB_PASSWORD` | `12345678` (dev fallback) | **Strong unique password** | Enforced by `ImproperlyConfigured` when `DEBUG=False`. |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` | Restricts cross-origin browser requests. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,...` | `https://app.collabai.io` | Whitelist of trusted frontend origins. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,...` | `https://app.collabai.io` | Whitelist for CSRF-protected POST/PUT/PATCH/DELETE. |
| `CELERY_TASK_ALWAYS_EAGER` | `true` | `false` | Forces async task offloading; prevents request blocking. |
| `GROQ_API_KEY` | Local dev key | **Rotated production key** | Rotate keys whenever an environment is suspected to have been exposed. |

### Recommended SSL / HSTS Hardening

| Variable | Dev Value | Production Value | Effect |
| :--- | :--- | :--- | :--- |
| `SECURE_SSL_REDIRECT` | `False` | `True` | Redirects all HTTP traffic to HTTPS. |
| `SECURE_HSTS_SECONDS` | `0` | `31536000` (1 year) | Instructs browsers to use HTTPS only. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | `True` | Applies HSTS to subdomains. |
| `SECURE_HSTS_PRELOAD` | `False` | `True` | Required for browser preload list inclusion. |
| `SECURE_PROXY_SSL_HEADER_ENABLED` | `False` | `True` (only behind a trusted reverse proxy) | Lets Django detect HTTPS via `X-Forwarded-Proto`. |

`SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are automatically enabled when `DEBUG=False` and require no manual change.

### Recommended Throttle Adjustments

| Variable | Default | Hardened |
| :--- | :--- | :--- |
| `THROTTLE_AUTH_LOGIN_RATE` | `5/minute` | `3/minute` (or `10/hour` per-IP for stricter brute-force blocking) |
| `THROTTLE_AUTH_REGISTER_RATE` | `3/minute` | `5/hour` |
| `THROTTLE_ANON_RATE` | `60/minute` | `30/minute` |

### Pre-Deployment Verification Steps

1. Run Django's deployment-readiness check:
   ```bash
   python manage.py check --deploy
   ```
2. Confirm that no secrets are present in source control:
   ```bash
   git log --all --full-history -- backend/.env
   ```
   (must return empty)
3. Ensure `.env` is listed in `.gitignore`.
4. Rotate `SECRET_KEY` and any third-party API keys (`GROQ_API_KEY`, etc.) before first deploy.
5. Verify that `docker-compose.yml` does **not** expose Postgres (`5432`) or Redis (`6379`) ports to the host network in production overrides.


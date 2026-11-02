# Quantova Finance

AI-powered financial intelligence platform for businesses, analysts, investors
and financial consultants: dashboards, income and expense tracking, profit and
loss analysis, cash flow forecasting, reporting and automated insights.

> **Status:** Phase 2 (backend core and authentication) complete. Next: Phase 3, frontend.

## Tech stack

| Layer          | Technologies                                                         |
| -------------- | -------------------------------------------------------------------- |
| Backend        | Python 3.14, FastAPI, SQLAlchemy 2.0 (async), Pydantic, Alembic, uv  |
| Data           | PostgreSQL 18, Redis 8                                               |
| Frontend       | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide              |
| AI             | LLM provider via adapter (OpenAI first)                              |
| Payments       | Stripe (sandbox during development)                                  |
| Infrastructure | Docker, Docker Compose, GitHub Actions                               |
| Quality        | Ruff, mypy (strict), pytest, ESLint, Prettier, Vitest, pre-commit, gitleaks |

## Repository layout

```
backend/
  app/
    api/            HTTP layer: routers and dependencies (auth, RBAC)
    core/           Settings, security (hashing, JWT), rate limiting
    db/             Engine, sessions, declarative base
    models/         SQLAlchemy models
    repositories/   Database queries
    schemas/        Pydantic request/response models
    services/       Business logic (one transaction per use case)
  alembic/          Database migrations
  tests/            Unit and integration tests
frontend/           React single-page application
infra/              Docker Compose services (PostgreSQL, Redis)
scripts/            Developer utilities (check.ps1)
```

## Prerequisites

- Windows 11 with PowerShell 7 (commands below are PowerShell)
- [uv](https://docs.astral.sh/uv/) (Python package manager; installs Python 3.14 automatically)
- Node.js (current LTS)
- Docker Desktop (WSL 2 backend)
- Git

## First-time setup

Run from the repository root unless stated otherwise.

**1. Infrastructure secrets.** Copy the template and replace each `change-me`
with a random value (hex only, so it is URL-safe). Run this once per password:

```powershell
Copy-Item infra/.env.example infra/.env
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
```

**2. Start PostgreSQL and Redis, and create the test database.**

```powershell
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec postgres createdb -U quantova quantova_test
```

**3. Backend.** Copy `backend/.env.example` to `backend/.env` and fill in every
value. Database and Redis passwords must match `infra/.env`. Generate
`JWT_SECRET_KEY` with:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Then install dependencies and create the schema:

```powershell
Set-Location backend
uv sync
uv run alembic upgrade head
Set-Location ..
```

**4. Frontend.**

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

**5. Git hooks.**

```powershell
.\backend\.venv\Scripts\pre-commit.exe install
```

## Daily development

Docker Desktop must be running. Use two terminals.

```powershell
# Terminal 1: API on http://127.0.0.1:8000 (interactive docs at /docs)
Set-Location backend
uv run uvicorn app.main:create_app --factory --reload

# Terminal 2: frontend on http://localhost:5173 (proxies /api to the backend)
Set-Location frontend
npm run dev
```

After pulling changes, run `uv sync` and `uv run alembic upgrade head` in `backend`,
and `npm ci` in `frontend`.

Before pushing, run every check that CI runs:

```powershell
./scripts/check.ps1
```

## Database migrations

Run in `backend`:

```powershell
uv run alembic revision --autogenerate -m "describe the change"   # 1. generate
# 2. review the new file in alembic/versions/ before applying it
uv run alembic upgrade head                                        # 3. apply
```

Never edit or delete a migration that has been applied to a shared or production
database; write a new migration instead. The test suite fails if models and
migrations disagree, or if a migration does not downgrade cleanly.

## Testing

Run in `backend`:

```powershell
uv run pytest                        # everything (needs PostgreSQL and Redis running)
uv run pytest -m "not integration"   # fast unit tests only, no services needed
```

Integration tests use `TEST_DATABASE_URL` and `TEST_REDIS_URL`, rebuild the test
schema from the migrations on every run, and refuse any database whose name does
not end in `_test`.

## API overview

| Area | Endpoints |
| ---- | --------- |
| Health | `GET /api/v1/health`, `GET /api/v1/health/ready` |
| Auth | `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `GET /api/v1/auth/me` |
| Organizations | `GET`/`POST /api/v1/orgs`, `GET`/`PATCH /api/v1/orgs/{org_id}` |
| Members | `GET`/`POST /api/v1/orgs/{org_id}/members`, `PATCH`/`DELETE /api/v1/orgs/{org_id}/members/{user_id}` |

Full interactive documentation is at `/docs` in development (disabled in production).

## Security model

- Passwords hashed with Argon2id; login timing and messages do not reveal which emails exist.
- 15-minute JWT access tokens; refresh tokens in HttpOnly, SameSite=Strict cookies,
  rotated on every use, with reuse detection that revokes the whole session.
- Organization-scoped RBAC (owner > admin > analyst > viewer); non-members receive 404.
- Append-only audit log, enforced by a database trigger.
- Redis-backed rate limits on login, registration and token refresh.

## Environment variables

Real values live in ignored `.env` files locally and in the hosting platform's
secret store in production. Templates (`.env.example`) are committed.

| File | Variable | Purpose |
| ---- | -------- | ------- |
| `infra/.env` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database container credentials |
| `infra/.env` | `REDIS_PASSWORD` | Redis container password |
| `backend/.env` | `ENVIRONMENT` | `development`, `test`, `staging` or `production` |
| `backend/.env` | `CORS_ORIGINS` | JSON list of allowed browser origins |
| `backend/.env` | `DATABASE_URL`, `REDIS_URL` | Application database and Redis |
| `backend/.env` | `TEST_DATABASE_URL`, `TEST_REDIS_URL` | Test database (name must end in `_test`) and Redis DB 1 |
| `backend/.env` | `JWT_SECRET_KEY` | Signs access tokens; 64 random hex characters |
| `backend/.env` | `RATE_LIMIT_ENABLED` | Optional; defaults to `true` |
| `frontend/.env.local` | `VITE_API_BASE_URL` | Optional. **Public**: never put secrets in `VITE_*` variables |

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `No pyproject.toml found` / `alembic.ini` not found | Run backend commands inside `backend/` |
| `ValidationError` for a setting on startup | `backend/.env` missing a value; compare with `backend/.env.example` |
| `Target database is not up to date` | Run `uv run alembic upgrade head` before generating a migration |
| Slow or failing DB connections | Use `127.0.0.1`, not `localhost`, in connection URLs |
| `failed to connect to the docker API` | Start Docker Desktop and wait until it is running |
| Login returns 429 during development | Wait for the window, or clear `ratelimit:*` keys in Redis |
| Frontend shows "API unreachable" | Start the backend (terminal 1) |

## Disclaimer

Quantova Finance provides financial analytics for informational purposes only.
AI-generated insights and forecasts are estimates, not guarantees or financial
advice.

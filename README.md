# Quantova Finance

AI-powered financial intelligence platform for businesses, analysts, investors
and financial consultants: dashboards, income and expense tracking, profit and
loss analysis, cash flow forecasting, reporting and automated insights.

> **Status:** Phase 1 (project foundation) complete. Next: Phase 2, backend core and authentication.

## Tech stack

| Layer          | Technologies                                                  |
| -------------- | ------------------------------------------------------------- |
| Backend        | Python 3.14, FastAPI, SQLAlchemy 2.0 (async), Pydantic        |
| Data           | PostgreSQL 18, Redis 8                                        |
| Frontend       | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide       |
| AI             | LLM provider via adapter (OpenAI first)                       |
| Payments       | Stripe (sandbox during development)                           |
| Infrastructure | Docker, Docker Compose, GitHub Actions                        |
| Quality        | Ruff, mypy (strict), pytest, ESLint, Prettier, Vitest, pre-commit, gitleaks |

## Repository layout

```
backend/    FastAPI application and tests
frontend/   React single-page application
infra/      Docker Compose services (PostgreSQL, Redis)
scripts/    Developer utilities (check.ps1)
docs/       Architecture notes and runbooks
```

## Prerequisites

- Windows 11 with PowerShell 7 (commands below are PowerShell)
- Python 3.14+
- Node.js (current LTS)
- Docker Desktop (WSL 2 backend)
- Git

## First-time setup

Run from the repository root unless stated otherwise.

**1. Infrastructure secrets.** Copy the template and replace both `change-me` values
with long random strings (hex characters only, so they are URL-safe):

```powershell
Copy-Item infra/.env.example infra/.env
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))  # run twice, one per password
```

**2. Start PostgreSQL and Redis.**

```powershell
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps   # both services should become (healthy)
```

**3. Backend.** Copy `backend/.env.example` to `backend/.env` and use the same
passwords as `infra/.env` in `DATABASE_URL` and `REDIS_URL`.

```powershell
Set-Location backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Set-Location ..
```

**4. Frontend.**

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

**5. Git hooks.** With the backend venv active:

```powershell
pre-commit install
```

## Daily development

Docker Desktop must be running. Use two terminals.

```powershell
# Terminal 1: backend API on http://127.0.0.1:8000 (docs at /docs)
Set-Location backend
python -m uvicorn app.main:create_app --factory --reload

# Terminal 2: frontend on http://localhost:5173 (proxies /api to the backend)
Set-Location frontend
npm run dev
```

Before pushing, run every check that CI runs:

```powershell
./scripts/check.ps1
```

## Environment variables

Real values live in ignored `.env` files locally and in the hosting platform's
secret store in production. Templates (`.env.example`) are committed.

| File | Variable | Purpose |
| ---- | -------- | ------- |
| `infra/.env` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database container credentials |
| `infra/.env` | `REDIS_PASSWORD` | Redis container password |
| `backend/.env` | `ENVIRONMENT` | `development`, `test`, `staging` or `production` |
| `backend/.env` | `CORS_ORIGINS` | JSON list of allowed browser origins |
| `backend/.env` | `DATABASE_URL` | `postgresql+asyncpg://user:password@127.0.0.1:5432/db` |
| `backend/.env` | `REDIS_URL` | `redis://:password@127.0.0.1:6379/0` |
| `frontend/.env.local` | `VITE_API_BASE_URL` | Optional. **Public**: never put secrets in `VITE_*` variables |

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `uvicorn`/`pytest` not recognized | Venv not active: `.\backend\.venv\Scripts\Activate.ps1`, or use `python -m uvicorn ...` |
| `ValidationError` for `database_url` on startup | `backend/.env` missing or incomplete; compare with `backend/.env.example` |
| Slow or failing DB connections | Use `127.0.0.1`, not `localhost`, in connection URLs |
| `failed to connect to the docker API` | Start Docker Desktop and wait until it is running |
| Frontend shows "API unreachable" | Start the backend (terminal 1) |

## Disclaimer

Quantova Finance provides financial analytics for informational purposes only.
AI-generated insights and forecasts are estimates, not guarantees or financial
advice.

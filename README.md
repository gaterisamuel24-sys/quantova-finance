if (Test-Path README.md) { Write-Host "STOP - README.md already exists" -ForegroundColor Red } else {
@'

# Quantova Finance

AI-powered financial intelligence platform for businesses, analysts, investors
and financial consultants: dashboards, income and expense tracking, profit and
loss analysis, cash flow forecasting, reporting and automated insights.

> **Status:** Phase 1 — project foundation (in progress)

## Tech stack

| Layer          | Technologies                                               |
| -------------- | ---------------------------------------------------------- |
| Backend        | Python, FastAPI, SQLAlchemy 2.0 (async), Pydantic, Alembic |
| Data           | PostgreSQL, Redis                                          |
| Frontend       | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide    |
| AI             | LLM provider via adapter (OpenAI first)                    |
| Payments       | Stripe (sandbox during development)                        |
| Infrastructure | Docker, Docker Compose, GitHub Actions                     |

## Repository layout

```
backend/    FastAPI application, migrations and tests
frontend/   React single-page application
infra/      Docker Compose and deployment configuration
docs/       Architecture notes and runbooks
```

## Local development

Setup instructions will be added as Phase 1 is completed.

## Disclaimer

Quantova Finance provides financial analytics for informational purposes only.
AI-generated insights and forecasts are estimates, not guarantees or financial
advice.
'@ | Set-Content -Path README.md -Encoding utf8NoBOM
}

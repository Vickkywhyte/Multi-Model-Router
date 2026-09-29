# Multi-Model Router — Roadmap

A FastAPI service that classifies prompt complexity and routes to the
cheapest capable Gemini model. Logs cost, latency, and quality.
Dashboard visualizes the spend-vs-quality tradeoff.

---

## Phase 1 — Project Skeleton
Create the full folder structure, meta files (README, .gitignore,
pyproject.toml, Makefile, Dockerfile, docker-compose.yml, .dockerignore,
.python-version, alembic.ini), and empty package folders with __init__.py.

**Done when:** `find` shows the full structure, `git status` is clean after
first commit. No application logic exists yet.

---

## Phase 2 — Config, Logging, App Entrypoint
- app/config.py (pydantic-settings, cached get_settings)
- app/observability/logger.py (structured JSON logging via python-json-logger)
- app/observability/tracing.py (request_id middleware)
- app/main.py (FastAPI app, CORS, lifespan, /health)
- app/api/v1/router.py (placeholder with /ping)
- .env.example

**Done when:** `make dev` boots the app and `curl /health` returns 200.

---

## Phase 3 — Database Layer
- app/db/base.py (DeclarativeBase)
- app/db/session.py (async engine + session factory)
- app/dependencies.py (re-export get_db, get_settings)
- migrations/env.py configured for async + Base.metadata
- Makefile targets: db-up, migrate

**Done when:** `docker compose up -d postgres && make migrate` succeeds.

---

## Phase 4 — ORM Models + Seed Script
- app/models/model.py (table: models)
- app/models/request.py (table: requests)
- app/models/quality.py (table: quality_scores)
- Alembic autogenerate migration
- scripts/seed_db.py (inserts Gemini models with real pricing)

**Done when:** `make migrate && make seed` succeeds; 3 rows in `models`.

---

## Phase 5 — Provider Abstraction
- app/providers/base.py (BaseProvider ABC + Pydantic DTOs)
- app/providers/gemini_provider.py (google-generativeai SDK implementation)
- app/providers/factory.py (provider registry)
- tests/unit/test_providers.py (mocked client)

**Done when:** `make test` passes with no real API calls.

---

## Phase 6 — Complexity Classifier
- app/core/classifier.py
- Rule-based (prompt length, keyword heuristics, question marks, code fences)
- Returns label ("simple" | "medium" | "complex") + reason
- tests/unit/test_classifier.py

**Done when:** classifier correctly routes 10+ sample prompts across labels.

---

## Phase 7 — Routing Service
- app/services/routing_service.py
- Orchestrates: classify -> pick model -> call provider -> log to DB -> return
- app/core/pricing.py (cost calculation from token counts)
- app/schemas/route.py (request/response Pydantic models)

**Done when:** service can be called from a test with a mocked provider.

---

## Phase 8 — /v1/route Endpoint
- app/api/v1/route.py (POST /v1/route)
- Wire into app/api/v1/router.py
- Integration test with mocked provider
- Add request_id response header

**Done when:** `curl -X POST /v1/route` returns a full response object.

---

## Phase 9 — /v1/requests + /v1/metrics Endpoints
- app/api/v1/requests.py (paginated list of logged requests)
- app/api/v1/metrics.py (spend, latency p50/p95, quality by model)
- app/services/metrics_service.py (SQL aggregations)
- scripts/benchmark.py (run same prompt through 3 models, print comparison)

**Done when:** `/v1/metrics/summary` returns real aggregates from logged data.

---

## Phase 10 — Quality Scoring
- app/api/v1/feedback.py (POST /v1/feedback)
- app/core/quality.py (pluggable: human score now, llm_judge later)
- tests for feedback flow

**Done when:** submitting a score updates the metrics endpoint.

---

## Phase 11 — Docker Polish + CI
- Multi-stage Dockerfile (non-root user)
- GitHub Actions: lint, typecheck, test on PR
- Pre-commit hooks (ruff, mypy)
- README polished with architecture diagram + quickstart

**Done when:** pushing a PR triggers CI, all checks green.

---

## Phase 12 — Dashboard
- dashboard/ (Next.js or Streamlit — decide at Phase 11)
- Charts: spend over time, cost vs quality scatter, model usage pie
- Reads from /v1/metrics endpoints

**Done when:** dashboard loads, shows real data, and deploys.

---

## Out of Scope (Post-MVP)
- Streaming responses
- Multi-tenant auth (OAuth / API keys)
- Rate limiting per user
- Prompt caching with Redis
- OpenAI provider (abstraction is ready; impl later)
- PII redaction in logs
- OpenTelemetry tracing

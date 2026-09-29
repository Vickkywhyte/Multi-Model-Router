# PRD — Multi-Model Router / AI Gateway

**Version:** 0.1 (MVP)
**Status:** Accepted
**Owner:** Solo Full-Stack Developer (Portfolio Project)
**Date:** 2026-01-01
**Related Docs:** ROADMAP.md · CLAUDE.md · ADR-001-tech-stack.md · API-CONTRACT.md

---

## 1. Problem Statement

Every team deploying LLMs faces the same dilemma:

- **Frontier models** (GPT-4-class, Gemini 2.5 Pro) deliver the best quality but
  cost 10–30x more per request than small models.
- **Small models** (Flash-Lite-class) are cheap and fast but fail on complex prompts.
- Teams either default to "always use the biggest model" (wasting money) or
  "always use the cheapest" (hurting quality).
- Most teams have **no systematic way to decide per request**, and no visibility
  into the cost/quality tradeoff after the fact.

The result is either overspend or underperformance — rarely the sweet spot.

---

## 2. Goal

Build a FastAPI service that:

1. Accepts a user prompt.
2. Classifies its complexity (simple / medium / complex).
3. Routes it to the **cheapest capable Gemini model** (Flash-Lite / Flash / 2.5 Pro).
4. Logs cost, latency, and quality score for every request.
5. Exposes metrics proving the spend-vs-quality tradeoff.

The service must be architected so any provider can be swapped in later
without touching business logic.

---

## 3. Target Users

| Persona | Why They Care |
|---|---|
| **Primary:** Engineering teams shipping LLM features | Need cost control without sacrificing quality |
| **Secondary:** Solo developers / indie hackers | Want a drop-in router they can self-host |
| **Tertiary (this project):** Me, the author | Portfolio piece demonstrating full-stack architecture, LLM orchestration, cost engineering, and observability |

---

## 4. Success Metrics (Measurable)

| Metric | Target |
|---|---|
| Average cost per request vs. always-2.5-Pro baseline | **≥ 50% reduction** |
| Quality score (human/LLM-judge) on medium + complex prompts | **≥ 4.0 / 5.0** |
| p95 latency for routed requests | **< 5 seconds** |
| Every request logged and queryable | **< 1 second query time** |
| Routing accuracy (classifier vs. human judgment on 20 test prompts) | **≥ 80% match** |

---

## 5. MVP Scope (v0.1)

### In Scope

**API**
- `POST /v1/route` — classify prompt, pick model, return completion + metadata
- `GET /v1/requests` — paginated history of logged requests
- `GET /v1/metrics/summary` — aggregates: spend, latency p50/p95, quality by model
- `POST /v1/feedback` — submit a quality score for a past request
- `GET /health` — liveness

**Core Logic**
- Rule-based complexity classifier (prompt length, keyword heuristics, code
  fences, question count)
- Provider abstraction via `BaseProvider` ABC
- One concrete provider: Google Gemini (Flash-Lite, Flash, 2.5 Pro)
- Cost calculation from token counts × per-model pricing
- Quality scoring framework with pluggable sources (human now, LLM-judge later)

**Data**
- Postgres for request logs, model pricing, quality scores
- Alembic migrations
- Seed script with current Gemini pricing

**DevEx**
- Docker Compose: app + postgres + redis
- Multi-stage Dockerfile (non-root user)
- Makefile: install, dev, test, lint, format, typecheck, migrate, seed, docker-up, docker-down
- pytest suite with mocked Gemini client (zero real API calls in tests)
- ruff + mypy + pre-commit
- GitHub Actions CI: lint + typecheck + test on PR
- Structured JSON logging with per-request `request_id`
- `scripts/benchmark.py` — runs same prompt through all 3 models, prints
  cost/latency/quality comparison table

### Out of Scope (Post-MVP / v0.2+)

- Streaming responses
- Multi-tenant auth (OAuth, API keys)
- Per-user rate limiting
- Redis prompt caching (infra provisioned, logic deferred)
- OpenAI / Gemini provider implementations (abstraction is ready)
- LLM-as-judge quality scoring (endpoint designed, pluggable)
- PII redaction in stored prompts
- OpenTelemetry distributed tracing
- Dashboard UI (Phase 12)
- Billing / usage metering

---

## 6. Non-Goals

- Being a production SaaS — no billing, no SLAs, no multi-region deploy.
- Beating every commercial router on features.
- Supporting every LLM provider on day 1.
- Replacing LangChain / LiteLLM — this is a focused router, not a framework.

---

## 7. Constraints

- **Solo developer, part-time build.**
- Must run locally with **one command** (`docker compose up`).
- Must not require paid infra beyond a **Gemini API key**.
- All LLM calls must be **async** (no blocking I/O).
- **Zero real API calls in the test suite** — all tests mock the Gemini client.
- Every file editable without needing a meeting — no team coordination overhead.

---

## 8. Acceptance Criteria (Definition of Done for MVP)

- [ ] `docker compose up` starts the whole stack with one command.
- [ ] `POST /v1/route` returns text + model used + tokens + cost + latency in one response.
- [ ] Every routed request appears in `GET /v1/requests`.
- [ ] `GET /v1/metrics/summary` shows cost, latency, and quality broken down by model.
- [ ] `POST /v1/feedback` records a quality score tied to a request_id.
- [ ] `scripts/benchmark.py` prints a Flash-Lite/Flash/2.5-Pro cost+latency table.
- [ ] All tests pass (`make test`) with no real API calls.
- [ ] CI is green on a PR (lint + typecheck + test).
- [ ] README explains the "why" in under 2 minutes of reading.
- [ ] `docs/architecture.md` contains a diagram and design rationale.

---

## 9. Open Questions (Decide During Build)

| Question | Decide By | Owner |
|---|---|---|
| Classifier: rule-based only, or add a tiny LLM call for edge cases? | Phase 6 | Me |
| Quality scoring default source: human-only or auto-heuristic first? | Phase 10 | Me |
| Dashboard framework: Next.js or Streamlit? | Phase 11 | Me |
| Cache strategy: full prompt hash vs. semantic similarity? | Post-MVP | Me |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Classifier misroutes simple prompts to expensive models | Cost blowup | Start rule-based, measure on 20-prompt test set, iterate |
| Classifier misroutes complex prompts to cheap models | Quality drop | Log every misroute as a quality score < 3, review weekly |
| Accidental real API calls in tests burn budget | Wallet pain | Enforce mocking in CLAUDE.md; CI fails on network calls |
| Scope creep (dashboard, auth, caching creep in early) | Never ship MVP | Roadmap phases are gates; PRD non-goals are the guardrail |
| Provider SDK breaking changes | Rework | Abstract behind `BaseProvider` — only one file to update |
| Postgres/Redis complexity slows local dev | Friction | docker-compose from Phase 1; no manual DB setup ever |

---

## 11. Release Plan

| Version | Scope | Target |
|---|---|---|
| **v0.1 (MVP)** | Phases 1–9 of ROADMAP.md | Routed requests + logging + metrics endpoint |
| **v0.2** | Phase 10 | Quality scoring + feedback loop |
| **v0.3** | Phase 11 | Docker polish + CI + README |
| **v1.0** | Phase 12 | Dashboard with spend-vs-quality charts |

---

## 12. Appendix: Why This Project Matters (Portfolio Framing)

Every company deploying LLMs at scale needs:
- **Model selection logic** (routing)
- **Cost observability** (logging + metrics)
- **Quality guardrails** (feedback + scoring)

This project demonstrates:

- **Product thinking** — this PRD itself.
- **Systems design** — layered architecture, provider abstraction, ADRs.
- **Full-stack range** — API, DB, migrations, containerization, CI, tests.
- **Cost engineering** — the core value proposition, measurable.
- **Discipline** — phased delivery, scope control, explicit non-goals.

> "I built a router that cut LLM cost per request by X% while keeping quality
> above 4.0/5.0 — here's the metrics endpoint that proved it."

---

**End of PRD.**
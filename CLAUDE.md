# CLAUDE.md — Instructions for Claude Code

This file is read by Claude Code on every session. Follow it strictly.

---

## Project
Multi-Model Router / AI Gateway. FastAPI service that classifies prompt
complexity and routes to the cheapest capable Gemini model
(Flash-Lite / Flash / 2.5 Pro). Logs cost, latency, and quality per request.

## Tech Stack (LOCKED — do not suggest alternatives without asking)
- Python 3.11, FastAPI, Pydantic v2
- SQLAlchemy 2.0 async + asyncpg + Alembic
- Postgres 16, Redis 7
- httpx, google-genai SDK
- python-json-logger (JSON structured logging via stdlib logging)
- pytest, pytest-asyncio, ruff, mypy
- Docker + docker-compose

## Architecture Rules (never violate)
- Layered: api/ → services/ → core/ → providers/
- api/ never imports from providers/ directly — go through services/
- Providers behind abstract BaseProvider interface
- SQLAlchemy models (app/models/) separate from Pydantic schemas (app/schemas/)
- Config only via app/config.py (pydantic-settings). No os.getenv() elsewhere.
- All LLM calls async
- Structured JSON logging only. Use app/observability/logger.py.

## Coding Conventions
- Type hints on every function signature
- Docstrings on public functions (Google style)
- No print() — use the logger
- Prefer explicit over clever
- Max function length ~40 lines; extract helpers if longer
- Every new module gets a test in tests/unit/ or tests/integration/

## Workflow Rules
- Work phase by phase. Do NOT scaffold future phases early.
- After each change run: `make lint && make test`. Fix failures.
- Never make real API calls in tests — mock the gemini client.
- Commit after each working phase with a clear message like:
  "phase N: <short description>"
- If unsure about a design decision, ASK before implementing.

## What NOT to Do
- Don't add features not asked for
- Don't add libraries without asking
- Don't refactor files outside the current task
- Don't modify .env (only .env.example)
- Don't touch the dashboard until backend MVP is done
- Don't write tests that call the real Gemini API

## Response Style
- After completing a task, output:
  1. A short summary of what changed
  2. A tree of files created/modified
  3. The exact verification command to run
- Then STOP. Wait for the next prompt.

## Current Phase
Read ROADMAP.md to determine the current phase. Check recent git log to
see which phase was last committed. The next phase is one after that.
Do not skip ahead.

## Protected Files (NEVER edit without explicit permission)
- CLAUDE.md — if you believe a rule needs to change, ASK FIRST and explain why.
- PRD.md
- ROADMAP.md

If any task seems to require changing these, STOP and ask. Do not edit silently.


## Provider Choice
Initial provider is **Google Gemini** (free tier), NOT Anthropic.
- Simple → gemini-3.5-flash-lite
- Medium → gemini-3.5-flash
- Complex → gemini-2.5-pro
- API key env var: GEMINI_API_KEY
- SDK: google-genai
- No paid tiers required. Design provider abstraction so Anthropic/OpenAI
  can be added later without touching business logic.

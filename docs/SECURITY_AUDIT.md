```markdown
# Pre-Deployment Security & Quality Audit
**Multi-Model Router — Phase 11 state**
Auditor review date: 2026-09-29

---

## 1. Security Concerns

### CRITICAL

**C-1 — `gemini_api_key` has a committed plaintext default**
- File: `app/config.py:28`
- The default value `"test-placeholder-key-not-used"` is committed to the repo. Any engineer who deploys without setting `GEMINI_API_KEY` ships a service that will call the Gemini API with a key that is known to anyone who ever reads the repo, forever. The comment says "tests mock the provider so the value is never used" — that is only true in the test runner. Uvicorn in production reads this default if the env var is missing, and the SDK call will fail loudly, but the default string is now permanently in git history.
- Recommended fix: Remove the default entirely (`gemini_api_key: str` with no default). Add a CI step that verifies the env var is set (`python -c "from app.config import get_settings; get_settings()"`). For tests, set `GEMINI_API_KEY=test-placeholder` in the CI environment or in pytest's `monkeypatch`. The string should never appear in source.

---

### HIGH

**H-1 — No authentication on any endpoint**
- Files: `app/main.py`, `app/api/v1/`
- Every endpoint — including `POST /v1/route` which makes paid Gemini API calls — is world-accessible with zero authentication. An attacker who discovers the host can drain the Gemini budget without limit.
- This is acknowledged as post-MVP in ROADMAP.md. That is the correct call for an internal prototype. Before any public exposure, API key authentication (a simple `X-API-Key` header checked via FastAPI middleware) must be added. Document this risk explicitly in the README so no one accidentally exposes this to the internet.

**H-2 — No rate limiting on `POST /v1/route`**
- File: `app/api/v1/route.py`
- The cost-per-attack for `POST /v1/route` on Gemini 2.5 Pro is $10.00/M output tokens. A single attacker can run a tight loop of complex prompts (score > 5 triggers Pro routing) and generate real API charges. There is no per-IP, per-key, or global rate limit.
- Recommended fix for pre-public deployment: Add a simple Redis-backed token bucket or use a middleware like `slowapi`. The infrastructure (Redis is already in the stack) makes this a 1-hour fix.

**H-3 — CORS is `allow_origins=["*"]` in development, and `app_env` defaults to `"development"`**
- File: `app/main.py:40-46`, `app/config.py:21`
- Because `app_env` defaults to `"development"`, any deployment that forgets to set `APP_ENV=production` silently runs with `allow_origins=["*"]`. A browser-based attacker on any origin can make credentialed requests to this API.
- Recommended fix: Invert the conditional — apply CORS restrictions unless `app_env == "production"`. Require `ALLOWED_ORIGINS` to be explicitly set for production; fail startup if it is empty in production mode.

**H-4 — `prompt_text` is stored verbatim in the database**
- File: `app/models/request.py:20` (comment: "PII — handle carefully in prod")
- The model acknowledges the risk but does nothing about it. The full user prompt is stored in plaintext in Postgres. If a prompt contains PII (names, emails, medical info), this is a GDPR/CCPA liability with no retention policy, no masking, and no TTL.
- The comment is not a control. Either store only the hash (already computed), or add a configurable PII scrubber before persistence. At minimum, document the data retention policy in README and require ops sign-off before production.

**H-5 — Database and Redis are exposed on the host network with default credentials**
- File: `docker-compose.yml:23, 36`
- Postgres is published on `0.0.0.0:5432` and Redis on `0.0.0.0:6379` with the password `postgres`. On any cloud VM with a default security group, both are reachable from the internet. No password is set for Redis.
- Recommended fix: Remove host port mappings from both services for any non-local environment. For developer convenience, use a `.docker-compose.override.yml` pattern to add ports locally without committing them to the main file. Set a strong `POSTGRES_PASSWORD` via `.env`. Add `requirepass` to Redis.

**H-6 — CI workflow runs on pull requests from forks**
- File: `.github/workflows/ci.yml:5-7`
- `on: pull_request: branches: [main]` triggers the workflow on PRs from forked repos. If any step ever adds secret access (e.g., a deployment step), a malicious PR can exfiltrate secrets. Currently there are no secrets in the workflow, so this is low-impact now but a latent risk.
- Recommended fix: Add `pull_request_target` only for trusted contributors, or restrict the workflow to `push` on `main` and approved PRs. GitHub's default behaviour (`pull_request`) does not expose secrets for forks, which is correct, but document this explicitly so the next engineer doesn't add secret access carelessly.

---

### MEDIUM

**M-1 — No input length or content limits on the `prompt` field**
- File: `app/schemas/route.py:12`
- `prompt: str` has no `max_length`. A caller can send a 1 MB string, which passes directly to Gemini. The cost scales with token count. Combined with the lack of rate limiting (H-2), this is an amplification vector.
- Recommended fix: Add `Field(..., max_length=32768)` or a configurable limit.

**M-2 — `request_id` in the feedback endpoint is unvalidated free text**
- File: `app/api/v1/feedback.py:11`, `app/schemas/feedback.py:11`
- `request_id` is `str` with no format constraint. The endpoint performs a parameterised query (safe from SQL injection), but a caller can submit arbitrary strings. The 404 response includes the raw `request_id` in the error detail: `f"request_id '{body.request_id}' not found"`. This echoes user input into the response body, which is a low-risk XSS vector if this API is ever consumed by a browser that renders the detail field.
- Recommended fix: Constrain `request_id` to UUID format with `Field(..., pattern=r'^[0-9a-f-]{36}$')`. Do not echo raw user input in error messages.

**M-3 — Docker image uses `python:3.11-slim` with no pinned digest**
- File: `Dockerfile:1,14`
- Both build stages use `:slim` without a digest pin. The image drifts silently when the upstream tag is updated. A supply chain compromise of the Python base image would affect the next build transparently.
- Recommended fix: Pin to a digest: `FROM python:3.11-slim@sha256:<digest>`. Automate digest updates with Dependabot or a weekly CI job.

**M-4 — Sensitive fields appear in logs**
- File: `app/services/routing_service.py:60-66`
- On provider error, `str(exc)` is logged. Depending on the Gemini SDK's exception formatting, this may include portions of the API key, request content, or internal URLs. The `error_message` column in the DB also stores `str(exc)` verbatim.
- Recommended fix: Log `type(exc).__name__` and a sanitised message. Never log raw exception strings from external SDK calls without reviewing what they contain.

---

### LOW

**L-1 — `.env.example` contains a realistic-looking placeholder API key**
- File: `.env.example:1` — `GEMINI_API_KEY=AIzaSy-your-key-here`
- The prefix `AIzaSy` is the real Google API key prefix. Automated secret scanners (truffleHog, GitHub push protection) may flag this even though it is a placeholder.
- Recommended fix: Use `GEMINI_API_KEY=your-google-ai-studio-api-key` without the realistic prefix.

**L-2 — No Content-Security-Policy or security response headers**
- File: `app/main.py`
- FastAPI does not add security headers by default. Absent auth and a browser client this is low priority, but add a middleware (`starlette-middleware` `SecurityMiddleware` or a simple dict-based middleware) before any dashboard is proxied through the same origin.

---

## 2. Code Quality & Engineering Judgment

### MAJOR

**Q-1 — `cost_usd` is stored as `float` in the ORM but calculated as `Decimal`**
- File: `app/models/request.py:29`, `app/services/routing_service.py:175`
- The ORM column is `Mapped[float]`, backed by `Numeric(10, 6)`. The service calls `float(cost_usd)` to persist. This converts a precise `Decimal` to an IEEE 754 float before writing to the DB. The same problem exists in `app/models/model.py:20-21` (`input_price_per_million: Mapped[float]`). Any aggregation done in Python after reading these floats will accumulate rounding error.
- Recommended fix: Change `Mapped[float]` to `Mapped[Decimal]` on `cost_usd` and price columns. SQLAlchemy's `Numeric` type maps to `Decimal` when `asdecimal=True` (the default). Remove the `float(cost_usd)` cast.

**Q-2 — `_persist_request` silently swallows DB errors after a successful completion**
- File: `app/services/routing_service.py:182-186`
- If the DB insert fails after a successful Gemini call, the user gets a valid response but the request is never logged. Cost, quality, and metrics are permanently lost. The error is logged but not surfaced.
- This is a deliberate design choice (documented in the docstring), but it's the wrong call. A DB failure on a successful completion should at minimum increment a counter so it can be alerted on. As written, the system can silently drop arbitrarily many records with no signal except checking the logs.
- Recommended fix: Return a flag from `_persist_request` indicating success or failure. Log a structured error with a `persist_failed=True` field that can be counted in a dashboard or alerted on.

**Q-3 — Two duplicate `_WINDOW_MAP` / `_WINDOW_HOURS` dicts across two files**
- Files: `app/api/v1/metrics.py:15-20`, `app/services/metrics_service.py:20-25`
- The same `{1h: 1, 24h: 24, 7d: 168, 30d: 720}` mapping appears twice with different variable names. If a new window is added, it must be added in both places. It is also inconsistent: the API layer validates the string against a regex pattern, converts it to hours using its local dict, then `metrics_service` converts hours back to a label using a reversed copy of its own dict. Three representations for the same concept.
- Recommended fix: Define the canonical dict once in `app/core/` (it is a business rule). Import it in both the API layer and the service.

**Q-4 — `get_provider()` instantiates a new provider on every call**
- File: `app/providers/factory.py:38`
- `return _REGISTRY[provider_name]()` creates a new `GeminiProvider` instance per request. Each `GeminiProvider.__init__` creates a new `genai.Client`. The Gemini SDK client may hold an HTTP connection pool; discarding it on every request wastes connection setup time and may create file descriptor pressure under load.
- Recommended fix: Cache provider instances (a module-level `_INSTANCES: dict[str, BaseProvider]`), or make `GeminiProvider` a singleton via `@lru_cache` on the factory function.

**Q-5 — `_persist_request` is called twice in `route_prompt` with near-identical argument lists**
- File: `app/services/routing_service.py:68-82`, `90-104`
- Two call sites differ only in `status`, `error_message`, and some metrics. This is copy-paste that will diverge. A future engineer adding a field (e.g., `user_id`) must remember to update both.
- Recommended fix: Build a `RequestPersistData` dataclass or TypedDict and pass it as a single argument.

---

### MINOR

**Q-6 — `Request` model has both a UUID `id` primary key and a `request_id` string column**
- File: `app/models/request.py:17-18`
- Two identity columns. `request_id` is what the application uses everywhere (it's the UUID4 string returned to callers, stored in quality_scores FK). The `id` PK is never referenced in any query. This is a dead column that adds confusion.

**Q-7 — `RouteRequest` accepts `temperature: float` with no bounds validation**
- File: `app/schemas/route.py:14-16`
- Gemini's `temperature` parameter is bounded 0.0–2.0. A caller can pass `temperature=999.0` and the SDK will likely reject it with an error that surfaces as a 500. Should be `Field(0.0, ge=0.0, le=2.0)`.

**Q-8 — `tracing.py` generates a `request_id` that is never the same as the `request_id` in the route response**
- Files: `app/observability/tracing.py:34`, `app/services/routing_service.py:40`
- The middleware generates one UUID for the HTTP request. The routing service generates a second UUID for the DB row. The response body `request_id` is the service's UUID, the `X-Request-ID` header is also the service's UUID (set in `route.py:47`), but the middleware's UUID is logged separately and also written to `X-Request-ID` (overwriting in `tracing.py:62`). In practice the middleware's header write wins because it runs after `call_next`. The result: the logged `X-Request-ID` in tracing logs doesn't match the `request_id` in routing logs or the DB row. Correlating a request across log lines requires knowing which UUID came from which system.

**Q-9 — `benchmark.py` uses `os.getenv` indirectly via `get_settings()` and also `sys.path.insert`**
- File: `scripts/benchmark.py:15-16`
- The `sys.path.insert` hack works but is fragile. If the project is properly installed (`pip install -e .`), it's unnecessary; if it's not installed, any other script also needs it. This is a script-specific concern, not a CLAUDE.md violation, but it signals that the project structure wasn't fully thought through for scripts.

---

### NITPICK

**N-1 — Docstrings on trivially obvious functions**
- Examples: `app/dependencies.py` has no functions but its module docstring explains re-exports. `app/db/base.py` presumably has a one-liner. `app/providers/base.py:44-46` — `complete()`'s docstring says "Send a prompt and return the completion." The name already says this.

**N-2 — `get_logger()` wraps `logging.getLogger()` with no added value**
- File: `app/observability/logger.py:34-43`
- The function has a docstring, a typed signature, and returns `logging.getLogger(name)`. It adds a layer of indirection so every module must import from `app.observability.logger` instead of `logging` directly. The only justification would be if it added context (request ID injection, sampling), but it doesn't.

**N-3 — `benchmark.py` uses `print()` directly in two places**
- File: `scripts/benchmark.py:81-82`, `91-101`
- CLAUDE.md bans `print()`. These are in a script, which is a grey area, but the script already imports and uses the logger.

**N-4 — `ClassificationResult` uses `dict[str, int]` for `scores` — a Pydantic model with known fields would be more type-safe**
- File: `app/core/classifier.py:27`
- The scores dict has a fixed set of known keys (`length`, `code_fences`, `question_marks`, etc.). A `ClassificationScores(BaseModel)` would make the fields explicit and catch typos.

**N-5 — `_build_reason` string construction logic (line 139) is hard to follow**
- File: `app/core/classifier.py:139`
- `" with ".join(parts[:1] + [", ".join(parts[1:])]).rstrip(" with")` — this is trying to produce "X with Y, Z" and strips the trailing " with" if there's only one part. The `rstrip` will also strip any reason string that happens to end in "with" (unlikely but possible). Use explicit branching: `if len(parts) == 1: return parts[0]; return f"{parts[0]} with {', '.join(parts[1:])}"`.

**N-6 — Test helper functions like `_make_mock_session`, `_make_mock_provider`, `_make_client`, `_cleanup` are duplicated across three integration test files**
- Files: `tests/integration/test_route_endpoint.py`, `tests/integration/test_feedback_endpoint.py`, `tests/integration/test_metrics_endpoints.py`
- Each file defines its own `_make_client()` and `_cleanup()` with slightly different signatures. This is the canonical use case for `tests/integration/conftest.py`, which is currently empty.

---

## 3. Architecture Review

**Provider abstraction: solid**
The `BaseProvider` ABC is genuinely provider-agnostic. Adding OpenAI or Anthropic requires exactly one new file. `calculate_cost`, `complete`, and `supports` are the right interface surface. No Gemini-specific types leak into `routing_service.py` or any API layer.

**Routing decision is tied to model name strings, not a tier abstraction**
`tier_to_model()` in `app/core/pricing.py` maps labels to model names, and `TIER_TO_MODEL` is the source of truth. But `_PRICING` in `gemini_provider.py` is a separate dict keyed by the same model names. If you add a fourth tier or rename a model, you must update both dicts independently. They are not linked. Adding OpenAI means duplicating this pricing structure inside `openai_provider.py` — there is no shared pricing registry.
The deeper issue: "simple → gemini-3.5-flash-lite" is a Gemini-specific routing decision encoded as a global truth in `core/pricing.py`. If you add OpenAI, which model maps to "simple"? The answer will be provider-specific, but the architecture has no slot for it.

**Pricing source of truth: split**
Three places hold pricing information:
1. `app/core/pricing.py` — TIER_TO_MODEL mapping
2. `app/providers/gemini_provider.py:14-18` — `_PRICING` dict (the one used for cost calculation)
3. `scripts/seed_db.py:22-43` — pricing data seeded into the DB
4. `app/models/model.py:20-21` — the DB columns that store pricing

If Gemini changes prices tomorrow, you must update `_PRICING` in the provider, `_MODELS` in the seed script, and re-run the seed. The DB values are never actually used by the cost calculation (the service ignores the `model_row.input_price_per_million` and calls `provider.calculate_cost()` instead). The DB has a pricing table that is completely decoupled from actual cost computation. This is the most significant architectural inconsistency in the codebase.

**Metrics scale: fine for MVP, will hurt at 10M rows**
All aggregations are in SQL, which is correct. `percentile_cont` in Postgres is a proper ordered-set aggregate. The `created_at` index is in place. The weakness: the per-model query joins `quality_scores` without filtering on `quality_scores.created_at` — it averages quality scores across all time regardless of the window. This means "avg quality in the last 1h" actually returns "avg quality since forever." Fixable with a `WHERE quality_scores.created_at >= since` condition.

**Layering: clean**
No `api/` → `providers/` imports were found. The layering rule is actually enforced, not just aspirational. Import paths follow `api → services → core/providers → models`.

---

## 4. Testing Quality

**What the tests actually verify:**
The tests verify correct HTTP status codes, response shape, and that mocked dependencies were called with the right arguments. This is appropriate for an integration test suite. The unit tests for the classifier are genuinely behaviour-focused (e.g., `test_design_architect_complex` constructs a real complex prompt and asserts it routes correctly). The cost calculation tests verify exact Decimal arithmetic — this is the right level of specificity for money.

**Tests that would pass even if the code were wrong:**
- `test_empty_prompt_returns_200` in `test_route_endpoint.py:130` — asserts only `status_code == 200`. An empty prompt classifies as "simple" and hits the provider. The test doesn't assert which model was selected, what the response contains, or whether the DB was written. It's a crash test, not a behaviour test.
- `test_medium_or_complex_multi_question` in `test_classifier.py:25` — asserts `result.label in ("medium", "complex")`. This would pass even if the classifier returned "complex" for everything above 10 words.

**Untested code paths that would break silently in production:**
- The `_persist_request` branch where `model_row is None` (line 158-163): the test `test_missing_model_row_does_not_crash` confirms it doesn't crash, but never verifies the warning was logged or that the response is still correct. More importantly: **no test verifies that the model DB row is actually missing causes the correct log warning.** In production, if the seed script was never run, every request silently drops its DB record with no alert.
- The `db_exc` branch in `_persist_request` (line 182): zero tests for this. A DB failure after a successful completion is completely untested.
- `QualityScore` duplicate submissions: the feedback endpoint has no uniqueness constraint or guard against submitting multiple scores for the same `request_id`. The `quality_scores` table has no unique index on `request_id`. The average score will be diluted by duplicates, but no test verifies this scenario.
- `metrics_summary` when there are zero requests: the endpoint returns zero totals, but `percentile_cont` on an empty set returns `NULL` in Postgres, which would cause `int(row.p50_latency_ms)` on line 145 to raise `TypeError`. Not tested.

**Mock realism:**
The mocks are at the right level — the Gemini SDK client is mocked, not the HTTP transport. The session mock is sufficient for unit tests. The main weakness: mock sessions in integration tests use `MagicMock()` without specifying `spec=AsyncSession`. This means any typo in a method call (e.g., `session.exeucte` instead of `session.execute`) will silently return another `MagicMock` instead of raising `AttributeError`. All session mocks should use `MagicMock(spec=AsyncSession)`.

**Missing coverage a senior reviewer would require:**
- No test for concurrent feedback submissions on the same `request_id`.
- No test for `metrics_summary` with zero requests in the window (the empty `percentile_cont` crash).
- No test verifying that DB persist errors don't affect the route response (the silent swallow).
- No test for the `tracing.py` middleware (the duplicate `X-Request-ID` bug described in Q-8 is untested).
- No test for `_hours_to_label` with an unknown hour value.

---

## 5. Operations & Reliability

**Cold start:**
On first deploy, `make migrate` must run before `uvicorn`. The `depends_on: service_healthy` in docker-compose handles Postgres readiness for the `app` service, but there is no migration step in the compose file or a startup health check that verifies migrations have run. If someone runs `docker compose up` without running `make migrate`, the app starts, Postgres is healthy, and the first request crashes at the DB query level with a "table does not exist" error. This is not caught at startup.

**Postgres down on startup:**
The `create_async_engine` call happens at module import time in `app/db/session.py:15`. SQLAlchemy's async engine does not connect at construction time — it lazily acquires connections on first use. So the app starts successfully if Postgres is down. The first request to any endpoint that uses `get_db()` will fail with a connection error, which surfaces as a 500. This is reasonable behaviour, but there is no `/readiness` probe (distinct from `/health`) that would let Kubernetes or load balancers know the DB is unavailable.

**Gemini API 500 or timeout:**
The routing service has no retry logic. A single transient 500 from Gemini returns a 500 to the caller immediately. The error is logged and the request is persisted with `status="error"`. For a free-tier API that may have higher variance, this is likely to produce visible errors under normal load. A bounded exponential backoff retry (2 attempts max) on 5xx would significantly improve reliability at essentially zero cost.

**Metrics to alert on:**
- `error_count / total_requests` ratio per window (currently available from `/v1/metrics/summary`)
- `p95_latency_ms` per model exceeding a threshold
- DB persist failures (currently not instrumented)
- Cost-per-request exceeding expected range (would indicate classifier misrouting)
- Response 500 rate at the HTTP layer (not currently instrumented — only app-level errors)

**Blast radius of a bad deploy:**
Moderate. Uvicorn serves until the worker crashes. A bad deploy that introduces a syntax error fails to import and the process exits; docker-compose restarts it. A bad deploy that introduces a runtime error on a specific code path will fail silently per request. There is no blue/green or canary in the current setup — any push to main that passes CI goes straight to whatever is running the compose stack.

**CI pipeline security:**
The current pipeline has no secrets and runs correctly scoped (no fork secret exposure). It does not cache pip dependencies between runs, so each run reinstalls all packages — this is slow (likely 2–3 minutes for pip alone) but safe. Adding `cache: pip` to the `setup-python` step would cut build time significantly with no security downside.

**Docker base image drift:** See M-3 above.

---

## 6. Signals of AI Generation or Junior Authorship

**Docstrings on trivially obvious functions:**
`get_logger()`, `get_settings()`, `ping()`, `register_provider()`, `get_provider()`, `tier_to_model()` all have multi-line Google-style docstrings. The functions are 1–5 lines. The docstrings are longer than the code they describe and add no information beyond what the name and type signatures already convey. A human who owns this code writes a one-liner or nothing.

**Every public function has a docstring regardless of triviality:**
This is a generated pattern. Humans apply judgment about when a docstring earns its keep. The uniform coverage is a tell.

**Two identity columns on the `Request` model (`id` and `request_id`):**
The `id` UUID PK is never queried. A human designing this schema would pick one. A generation step that added "standard ORM boilerplate" and then a separate step that added "application-level request tracking" produces this duplication without noticing.

**Empty conftest files:**
`tests/conftest.py`, `tests/integration/conftest.py`, `tests/unit/conftest.py` all contain only a docstring. Shared fixtures (`_make_client`, `_make_mock_session`) that are duplicated across three test files belong there. These files exist as stubs that were never filled.

**Duplicate helper functions across test files:**
`_make_client()` and `_cleanup()` are defined in all three integration test files with slight variations. This is a direct consequence of the empty conftest files. A human writing the second test file would have extracted the helpers.

**`get_logger()` wrapper with no added value:**
Wrapping `logging.getLogger()` in a function that only adds a docstring is something a model does to make the observability layer look more sophisticated than it is.

**Classifier hash computed twice:**
`app/core/classifier.py:91` computes `prompt_hash` only to include it in a debug log, then throws it away. `app/services/routing_service.py:46` computes the same hash again to store it in the DB. This is not a bug but is a sign of two independently written functions that don't share data.

**`benchmark.py` uses `print()` despite the project banning it:**
The ban is in CLAUDE.md. A human who wrote the file would know the project's conventions. A model generating the script independently produced the most natural output-to-terminal code without cross-checking the project rules.

**The `_WINDOW_MAP` duplication (described in Q-3):**
Two modules independently defined the same constant. A human writing the second module would have noticed the first during implementation. A generation step that wrote each module in isolation would not.

---

## 7. Strengths Worth Preserving

- **Provider abstraction is genuinely clean.** `BaseProvider` with `complete()`, `calculate_cost()`, and `supports()` is the right interface. Adding a second provider requires zero changes to business logic. Do not add provider-specific logic to `core/` or `services/`.

- **Decimal arithmetic throughout the cost pipeline.** The calculation in `gemini_provider.py:94-97` is exact. The service passes `Decimal` through without conversion. The float cast at persistence (Q-1) is the only breach of this discipline, and it's fixable in one line.

- **SQL aggregations, not Python aggregations.** `metrics_service.py` delegates `percentile_cont`, `sum`, `avg`, and `count` to Postgres. At 10M rows this is still fast because none of the data is pulled into Python. The pattern is correct and must not be changed to in-memory aggregation.

- **Layering is actually enforced.** The import graph is clean: `api → services → core/providers → models`. No violations were found. This is rarer than it sounds.

- **Structured JSON logging with no f-strings in log calls.** Every `logger.info()` call passes structured `extra={}` dicts, not interpolated strings. This means log fields are queryable in any log aggregation system without regex parsing. Preserve this strictly.

---

## 8. Top 10 Fix List (Priority Order)

| # | Description | Files | Effort |
|---|---|---|---|
| 1 | Remove `gemini_api_key` default; set it in CI via env var instead | `app/config.py`, `.github/workflows/ci.yml` | 15 min |
| 2 | Fix `cost_usd` and price columns: `Mapped[float]` → `Mapped[Decimal]`, remove `float()` cast | `app/models/request.py`, `app/models/model.py`, `app/services/routing_service.py` | 1 hr |
| 3 | Add rate limiting to `POST /v1/route` using Redis token bucket | `app/api/v1/route.py`, `app/main.py` | 1 hr |
| 4 | Fix the `quality_scores` window filter in `metrics_summary` (quality is averaged across all time, not the window) | `app/services/metrics_service.py:123-124` | 15 min |
| 5 | Add `max_length` to `prompt`, `ge/le` to `temperature`, and UUID pattern to `request_id` in schemas | `app/schemas/route.py`, `app/schemas/feedback.py` | 30 min |
| 6 | Resolve the duplicate `_WINDOW_MAP` / `_WINDOW_HOURS` constant; add a test for the empty-window `percentile_cont` NULL crash | `app/core/`, `app/api/v1/metrics.py`, `app/services/metrics_service.py`, `tests/` | 1 hr |
| 7 | Move shared test fixtures to `tests/integration/conftest.py`; add `spec=AsyncSession` to all session mocks | `tests/integration/conftest.py`, all three integration test files | 1 hr |
| 8 | Remove host port mappings for Postgres and Redis from `docker-compose.yml`; add Redis password | `docker-compose.yml` | 15 min |
| 9 | Instrument DB persist failures with a counter or structured log field that can be alerted on | `app/services/routing_service.py` | 30 min |
| 10 | Fix the `X-Request-ID` collision between middleware and route handler: use a single request ID, passed via request state | `app/observability/tracing.py`, `app/api/v1/route.py`, `app/services/routing_service.py` | 1 hr |
```

Written for: the engineer who will act on it — specific file references, no softening, no invented issues.

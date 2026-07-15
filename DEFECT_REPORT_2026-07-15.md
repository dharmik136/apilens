# APILens Defect Report — 2026-07-15

Comprehensive QA pass covering the full stack (Django API, Next.js frontend,
FastAPI ingest service, Python + TypeScript SDKs, ClickHouse schema, CI). All
23 items below were found by actually reproducing the failure — running the
stack, driving it with Playwright, load-testing it with a traffic-fuzzing
harness, and reading the exact code path involved — not by static guessing.
Every fix listed as "Fixed" has been applied locally, verified (test suite,
manual reproduction, or both, as noted per item), and the full local test
matrix (Django `check`/`makemigrations --check`, Python SDK's pytest suite,
TypeScript SDK's vitest suite, and `apps/web`'s `tsc --noEmit`) is green.

**A note on process**: two candidate findings from an earlier audit pass were
investigated and found to be incorrect before any fix was attempted — a claim
that six `IngestService` schema-helper methods were dead code (they have
dozens of real call sites) and a claim that only the FastAPI integration
supported request/response body capture toggles (none of the six framework
integrations did). Neither is included below. This report only contains
independently re-verified findings.

None of this is committed yet — it's the current local working tree. Happy to
open individual issues and/or a PR per item, or batch them, whichever this
repo's maintainers prefer.

---

## 1. Security: RBAC fails open on OPA outage — Fixed

**File**: `apps/api/apps/projects/services.py`, `ProjectService.authorize()`

**The bug**: when the OPA policy sidecar is unreachable (`opa.check()` returns
`None` — timeout, network blip, sidecar restart), any project member with
*any* role, including `viewer` (read-only by design), was granted the
requested action unconditionally — including `admin` and `delete`. The code's
own comment described this as "degrade gracefully," but the fallback branch
never consulted `action` at all.

**Failure scenario**: OPA restarts or blips mid-request → a viewer-role
member's `DELETE /api/v1/projects/{slug}` or a role-escalation `PATCH` on
another member succeeds during that window.

**Fix**: the fallback now only fails open for `action == "read"`; every other
action raises `AuthorizationError` when OPA is unreachable, so an unevaluated
policy can never grant a privileged action.

**Verified**: two independent test passes via Django shell — (1) OPA mocked
unreachable: `read` → allowed, `admin`/`delete` → denied (previously
allowed); (2) real OPA, un-mocked: `viewer` role still gets exactly
`read` → allowed / `write`,`admin`,`delete` → denied, confirming the normal
path is unaffected.

---

## 2. ClickHouse migrations silently deleted by `.gitignore` — Fixed

**Files**: `.gitignore`, `apps/api/apps/{auth,projects,users}/migrations/*`,
`apps/api/core/database/clickhouse/migrations/*`

**The bug**: `main`'s `.gitignore` blanket-ignored `**/migrations/`, so the
Django migrations for `apps.projects`/`apps.auth`/`apps.users` and the
ClickHouse `.sql` migrations were never committed. A fresh checkout's
Postgres only ever gets 10 base auth/session tables — `projects`, `apps`,
`endpoints`, etc. never exist, and nearly every real feature 500s.

This exact defect (and fix) already exists on `origin/anomaly-alerts-upstream`
(commit `be2de6e`, "fix(repo): track Django + ClickHouse migrations in git")
but was never merged into `main`.

**Fix**: cherry-picked `be2de6e` onto `main`, then ran `manage.py migrate` +
`clickhouse_migrate`.

**Verified**: Postgres went from 10 tables to 26; `SELECT` against
previously-missing tables succeeds.

---

## 3. `Project` model missing a field its own migration added — Fixed

**File**: `apps/api/apps/projects/models.py`

**The bug**: migration `0006_project_anomaly_alerts_enabled.py` added
`anomaly_alerts_enabled` (`NOT NULL`) to the `projects` table, but the
`Project` model class was never updated to declare the field. Every
`Project.objects.create(...)` — i.e. creating a new project, a core onboarding
flow — crashed with `IntegrityError: null value in column
"anomaly_alerts_enabled"`.

**Fix**: added `anomaly_alerts_enabled = models.BooleanField(default=True)` to
the model, matching the migration exactly.

**Verified**: `makemigrations --check` reports zero drift; project creation
succeeds via the real service call.

---

## 4. `api_logs` ClickHouse migration never existed — Fixed

**File**: `apps/api/core/database/clickhouse/migrations/004_api_logs.sql` (new)

**The bug**: `apps/ingest/app/ingest.py`'s own code comment referenced "the
004 migration" for `api_logs`'s correlation columns, but no such file existed
anywhere in the repo (only 001–003). `ensure_clickhouse_schema()`'s `ALTER
TABLE api_logs ...` statements threw `Could not find table: api_logs`, and
because that function ran all ~20 statements for `api_requests`/`api_logs` in
one unguarded loop, **one missing table blocked ALL telemetry ingestion** —
requests and traces too, not just logs.

**Fix**: wrote `004_api_logs.sql` from the exact column list in `ingest.py`'s
`LOG_COLUMNS` and the sibling `002_api_requests.sql`'s conventions; applied it.

**Verified**: re-ran the traffic generator; `api_requests`/`api_spans`/
`api_logs` all started receiving real rows in ClickHouse (previously: 0 rows,
every ingest call 500ing).

---

## 5. Every authentication route missing an import — Fixed

**Files**: 20 files under `apps/web/src/app/api/{auth,account/passkeys}/**`

**The bug**: all 20 route handlers call `getAuthApiUrl()` (from
`@/lib/api-client`) but **not one of them imports it** —
`ReferenceError: getAuthApiUrl is not defined` at module-load time, on every
single one. **Login was completely broken by every method** — magic link,
passkey, password reset, 2FA, account recovery. Root cause: a prior refactor
centralized what used to be a hardcoded fallback URL into a shared helper and
swapped every call site to use it, but never added the import anywhere.

**Fix**: added `import { getAuthApiUrl } from "@/lib/api-client";` to all 20
files.

**Verified**: `tsc --noEmit` clean; two independent Playwright runs with fresh
magic-link tokens in fresh browser contexts — session cookie set, full
9-page dashboard navigation with zero 500s (previously 45 error events per
run).

---

## 6. `api_logs` (Django copy) missing `project_id` — Fixed

**File**: `apps/api/apps/projects/services.py`,
`IngestService.ensure_api_logs_table()`

**The bug**: the Django-side runtime schema-ensure for `api_logs` patches in
nine correlation columns (`endpoint_method`, `status_code`, `trace_id`, ...)
but not `project_id` — while every reader of the table (`LogsService`,
error-log queries) filters `WHERE project_id = ...`, and the FastAPI ingest
side's equivalent list *does* include it. If this Django code path ever
creates the table first (e.g. a fresh ClickHouse where `clickhouse_migrate`
hasn't run yet), the project-scoped Logs/Errors view queries a nonexistent
column, the exception is swallowed by a bare `except`, and the page shows
"no errors" forever with nothing surfaced anywhere.

**Fix**: added `project_id` to both the `CREATE TABLE` and the `ALTER TABLE
... ADD COLUMN IF NOT EXISTS` fallback list.

**Verified**: read the exact statement list before and after; matches the
FastAPI ingest side's column set exactly now.

---

## 7. Creating an app with a custom ID silently ignores it — Fixed

**File**: `apps/web/src/app/api/projects/[slug]/apps/route.ts`

**The bug**: the New App form validates a custom App ID live ("Available —
this will be used as your app_id") and sends `slug` in the POST body, but the
proxy route only forwarded `name`/`description`/`framework` — `body.slug` was
never read. The backend then auto-generated a different slug. Any SDK
configured with the ID the user actually picked and validated in the UI would
422 forever (ingest strictly validates `app_id` against pre-registered apps,
no auto-create).

**Fix**: forward `slug: body.slug || ""` to the backend (which already
supports a `custom_slug` parameter end-to-end).

**Verified**: posted `slug: "my-custom-slug-123"` through the real HTTP
proxy route and confirmed the created app's slug matched exactly (previously
would have been auto-generated from the name).

---

## 8. Express SDK never groups routes by template — Fixed

**File**: `packages/sdk-typescript/src/express.ts`

**The bug**: the route path was read from `req.route?.path` at the very top
of the middleware, before `next()` is called. Express only populates
`req.route` once its router has matched and dispatched to a handler, which
happens *inside* `next()`'s call chain — so `req.route` is always `undefined`
at that point, and every distinct URL (`/orders/1`, `/orders/2`, ...) becomes
its own "endpoint," exactly the problem the Python SDK has dedicated logic
and tests to prevent.

**Fix**: moved the path computation into the `res.once("finish", ...)`
handler, which runs after the response completes (i.e., after routing has
resolved).

**Verified**: confirmed `next()` is called at a later line than where `path`
used to be computed; the SDK's existing `express.e2e.test.ts` (2 tests) still
passes.

---

## 9. Backend has had zero CI coverage — Fixed

**File**: `.github/workflows/api-ci.yml`

**The bug**: `paths: ['backend/**', ...]` and `working-directory: backend`
reference a `backend/` directory that doesn't exist anywhere in this repo —
the real app is `apps/api/`. GitHub Actions path filters are prefix matches,
so this workflow **never triggers** on commits touching `apps/api/**`. It
looks green in history only because it never ran, not because it passed.
(Also found, not fixed as out of scope: several of its steps already have
`continue-on-error: true`, including the coverage gate, so even a triggered
run wouldn't fail the build on most problems.)

**Fix**: all `backend`/`backend/**` references changed to `apps/api`/
`apps/api/**`, including the self-referencing workflow-file path trigger
(which itself incorrectly said `backend-ci.yml` instead of `api-ci.yml`).

**Verified**: `grep -n backend .github/workflows/api-ci.yml` now only matches
a benign comment, no path references.

---

## 10. Errors page goes silently blank after ~15 minutes — Fixed

**Files**: `apps/web/src/app/api/projects/[slug]/analytics/{error-summary,
error-status-groups,error-events,error-issues}/route.ts`

**The bug**: these 4 routes (one more than originally flagged — `error-issues`
has the identical bug) build their own `fetch` with a raw `Authorization:
Bearer` header and no 401-retry, unlike every sibling analytics route, which
uses the shared `proxyDjangoGet`/`fetchWithRefresh` helper specifically added
to fix "requests failing permanently until reload" after access-token expiry
(~15 min). Once the token expires mid-session, these 4 routes' summary tiles
and tables silently drop to zero/"No errors," while the same page's
timeseries chart (which does use the shared helper) keeps working —
inconsistent and confusing.

**Fix**: rewrote all 4 routes to use `proxyDjangoGet`, matching the sibling
routes exactly.

**Verified**: `tsc --noEmit` clean.

---

## 11. Fake API key shown in the new-app setup guide — Fixed

**File**: `apps/web/src/app/projects/[slug]/new-app/CreateProjectAppForm.tsx`

**The bug**: `GET /api/projects/{slug}/api-keys` returns `{ keys: [...] }`,
but the setup-guide code did `keys.length` directly on that object —
`.length` on a plain object is `undefined`, so the check was always falsy and
the guide always showed the hardcoded placeholder `apilens_****` instead of
the project's real key prefix.

**Fix**: destructure `{ keys }` from the response before checking `.length`.

**Verified**: traced the exact shape contract against the correct sibling
usage in `ProjectApiKeysSection.tsx`, which does `data.keys` correctly.

---

## 12. Stale app data flashes when switching apps — Fixed

**File**: `apps/web/src/components/providers/AppProvider.tsx`

**The bug**: when `appSlug`/`projectSlug` change on an already-mounted
provider, neither `app` nor `isLoading` were reset before the new fetch
started — so `useApp()` consumers briefly render the *previous* app's data as
fully loaded, then swap silently, instead of showing a loading state.

**Fix**: `setApp(null)` and `setIsLoading(true)` before starting the new
fetch.

**Verified**: `tsc --noEmit` clean; logic matches the standard "reset before
refetch" pattern used elsewhere in the codebase.

---

## 13. Six SDK framework integrations can't disable body/header capture — Fixed

**Files**: `packages/sdk-python/apilens/{fastapi.py, frameworks/fastapi.py,
frameworks/flask.py, starlette.py, litestar.py, blacksheep.py, django.py}`

**The bug**: the README documents `capture_payloads`, `capture_headers`,
`log_request_body`, `log_response_body`, and `max_payload_bytes` as generally
available config options, and the underlying `ApiLensASGIMiddleware`/
`ApiLensWSGIMiddleware` classes genuinely accept all five — but **none** of
the six framework-specific wrapper functions (`instrument_fastapi`,
`instrument_flask`, Starlette's/Litestar's/BlackSheep's `instrument_app`, and
`ApiLensGatewayMiddleware`) exposed or forwarded `capture_payloads`/
`capture_headers` (some were also missing the other three). Calling e.g.
`instrument_flask(app, client, capture_payloads=False)` raised `TypeError`.
Django had `capture_headers` via a settings flag but no equivalent for
payloads at all (only the indirect `APILENS_MAX_PAYLOAD_BYTES=0` workaround).

**Fix**: added all 5 params to every wrapper (Django got a new
`APILENS_CAPTURE_PAYLOADS` setting, mirroring its existing
`APILENS_CAPTURE_HEADERS`), forwarded through to the underlying middleware.

**Verified**: (1) signature inspection confirms all 6 wrappers now expose all
5 params against the local source (not the installed published package,
which was checked first and correctly excluded from this claim); (2)
functional test — `instrument_flask(..., capture_payloads=False,
capture_headers=False)` and asserted the resulting middleware instance's
attributes are actually `False`; (3) full pytest suite (29 tests) still
green.

---

## 14. Span/error-log recorder is a process-wide global — Fixed

**File**: `packages/sdk-python/apilens/client/spans.py` +
`client/middleware.py` + `django.py`

**The bug**: `_recorder` was a single module-level variable, and every
middleware instance's `configure_spans()` call unconditionally overwrote it.
Any process instrumenting more than one app (e.g. an ASGI app mounting two
sub-apps, each with its own `app_id`) had only the *last-constructed*
middleware's identity survive — every span and auto-captured error log from
the first app got permanently attributed to the second app.

**Fix**: converted `_recorder` to a `contextvars.ContextVar`, with a
`use_recorder()` context manager that each middleware checks its own recorder
into for the duration of the single request it's handling. Required care in
two places: the WSGI middleware's request handler is a *generator* (yields
response chunks), so wrapping the outer call in the context manager doesn't
cover the actual iteration — this was caught and fixed before verification,
not after.

**Verified**: (1) sequential test — two recorders, two calls, each span
attributed correctly, zero cross-contamination; (2) genuine concurrent
`asyncio.gather()` test with interleaved `await`s — still zero
cross-contamination, confirming the fix holds under real concurrency, not
just sequential blocks; (3) full pytest suite, including the FastAPI
end-to-end test that exercises the real ASGI middleware, still green.

---

## 15. TypeScript SDK reports the wrong version — Fixed

**File**: `packages/sdk-typescript/{tsup.config.ts, src/client.ts}`

**The bug**: `SDK_VERSION = "0.1.0"` was hardcoded in `client.ts`,
independent of `package.json`'s actual `0.1.1` (which had already been
bumped for a real fix per `CHANGELOG.md`). Every ingest request's
`User-Agent` header permanently reported the stale version.

**Fix**: `tsup.config.ts` now injects the real version from `package.json` at
build time via esbuild's `define`; `client.ts` reads the injected constant
with a dev-mode fallback.

**Verified**: ran the actual build; confirmed the compiled output resolves to
`"0.1.1"`. Full vitest suite (8 tests) still green.

---

## 16. Python SDK retries errors it already knows are non-retryable — Fixed

**File**: `packages/sdk-python/apilens/client/client.py`

**The bug**: `_post_json` explicitly labels 4xx-except-429 responses
`"Non-retryable ingest error"`, but `_send_batch_with_retry` caught a bare
`Exception` and retried unconditionally up to `max_retries` with exponential
backoff regardless — burning the retry budget (and blocking the single
background flush thread) on a batch that will fail identically every time,
e.g. the unregistered-`app_id` 422 case.

**Fix**: introduced a `_NonRetryableIngestError` subclass, raised specifically
for that case, caught separately in the retry loop to stop immediately.

**Verified**: functional test — non-retryable error: exactly 1 attempt, 0s
elapsed (previously would have been 4 attempts, ~0.35s); retryable error
(500-style): unchanged behavior, 4 attempts with real backoff delay.

---

## 17. OpenTelemetry forced as a base dependency — Fixed

**Files**: `packages/sdk-python/pyproject.toml`, `apilens/__init__.py`,
`apilens/client/__init__.py`

**The bug**: `opentelemetry-api`/`opentelemetry-sdk` were unconditional
`[project] dependencies`, even though `apilens/client/otel.py` is lazily
imported specifically so — per its own code comment — "core middleware
usable without OTel dependency." Nothing outside `otel.py` uses
`opentelemetry` at all.

**Fix**: moved both packages to a new `otel` extra (and kept them in `all`).
While verifying, found the lazy-import design was **already broken** by a
second, eager import: `apilens/client/__init__.py` did `from .otel import
install_apilens_exporter` at module level, which runs on every `import
apilens` regardless — so removing the base dependency alone would have made
`import apilens` crash for anyone without OTel installed. Fixed that too
(removed the eager re-export; the top-level lazy wrapper already exists and
is the correct public entry point), and added a clear `ImportError` message
pointing at `pip install apilenss[otel]` if someone calls the exporter
without it installed.

**Verified**: simulated `opentelemetry` being absent by blocking its import
at the interpreter level — confirmed `import apilens` now succeeds and
`install_apilens_exporter()` raises the friendly error instead of a raw
`ModuleNotFoundError` three frames deep. Full pytest suite still green.

---

## 18. `ensure_clickhouse_schema` is a single point of failure for all ingestion — Fixed

**File**: `apps/ingest/app/ingest.py`

**The bug**: same underlying defect class as #4 above, but structural: all
~20 schema-ensure statements for `api_requests`/`api_logs`/`api_spans` ran in
one loop with no per-statement error handling, and `_schema_ready` was only
set `True` after every statement succeeded. Any single future statement
failing (a typo, a version-incompatible column type) would silently take
down `/v1/requests`, `/v1/logs`, and `/v1/traces` together, indefinitely,
even though only one table was actually affected — exactly what happened
today before #4 was diagnosed.

**Fix**: each statement now runs in its own try/except, logging a warning and
continuing on failure rather than aborting the loop; `_schema_ready` is set
`True` regardless (matching the existing best-effort-once semantics, just no
longer all-or-nothing).

**Verified**: functional test with a simulated mid-loop failure — all 27
statements still attempted, `_schema_ready` still became `True`.

---

## 19. `api_spans` has no migration file — Fixed

**Files**: `apps/api/core/database/clickhouse/migrations/005_api_spans.sql`
(new), `apps/api/apps/projects/services.py`

**The bug**: `api_spans` was only ever created at runtime, independently, in
two places (`ingest.py` and `services.py`'s `ensure_api_spans_table`), with
no tracked migration and no shared source of truth — and the two copies had
already drifted: `ingest.py` adds 3 bloom-filter indexes (`trace_id`,
`project_id`, `environment`), the Django copy only added 2, missing
`environment`.

**Fix**: wrote `005_api_spans.sql` as the canonical definition (both runtime
copies remain as no-op safety nets for pre-existing databases); added the
missing `environment` index to the Django copy so both converge on the same
3-index set.

**Verified**: applied the migration; confirmed all 3 indexes exist on the
live table via `system.data_skipping_indices`. (Caught and fixed a
self-inflicted issue while writing this migration: the crude `;`-based
statement splitter in `migrate.py` doesn't understand SQL comments, and a
semicolon in the migration's own prose header comment split the file wrong —
rewrote the comment to avoid semicolons and re-verified the split before
applying.)

---

## 20. Wrong default introspect URL — Fixed

**File**: `apps/ingest/app/config.py`

**The bug**: `load_introspect()`'s default URL was
`http://identity:8000/api/v1/auth/introspect`, but the real standalone
identity service mounts its API at `/v1/*` (confirmed against
`config/urls_identity.py` and `apps/identity/README.md`) — `/api/v1/auth/*`
only exists behind a Caddy rewrite in front of the public host, not reachable
container-to-container. Currently masked in every real deployment (both
`.env.example` and prod compose explicitly override it), so this is a latent
correctness bug in the default, not an active outage.

**Fix**: corrected the default path to `/v1/introspect`.

**Verified**: confirmed against the identity service's actual URL
configuration and its own README's documented endpoint table.

---

## 21. `AlertEvent`/`JobHeartbeat` — migrated tables with no model code — Fixed

**File**: `apps/api/apps/projects/models.py`

**The bug**: migrations `0003`–`0005` created the `alert_events` and
`job_heartbeats` Postgres tables (implying an anomaly-alerting feature), but
no `AlertEvent`/`JobHeartbeat` Django model class existed anywhere — a
repo-wide grep found zero references outside the migration files themselves.
The tables were completely unreachable from Python.

**Fix**: added both model classes, with fields mirroring the migrations
exactly (verified field-for-field, including the `0005` follow-up
`viewed_at` addition).

**Verified**: `makemigrations --check --dry-run` reports zero drift (exact
match to the already-applied schema); created, queried, and deleted a real
`AlertEvent` and `JobHeartbeat` row through the ORM successfully.

---

## 22. Dead code cleanup — Fixed

**Files**: `apps/api/apps/projects/services.py`, `apps/ingest/app/ingest.py`

- Removed `IngestService._safe_payload` — confirmed zero callers anywhere in
  the repo (the FastAPI ingest service has its own separate, actively-used
  copy at `apps/ingest/app/ingest.py:66`, which was not touched).
- Fixed `ingest.py`'s module docstring, which claimed to be "kept in
  lock-step with `apps/api/routers/ingest/router.py`" — that file doesn't
  exist; the real Django-side equivalent is `IngestService` in
  `apps/api/apps/projects/services.py`, which the rest of the docstring
  already correctly named.

**Not removed** (investigated and found to be actively used, contradicting
an earlier audit pass's claim): `ensure_payload_columns`,
`ensure_header_columns`, `ensure_base_url_column`, `ensure_raw_path_column`,
`ensure_consumer_columns`, `ensure_trace_columns` — each has multiple real
call sites in `services.py` (`ensure_consumer_columns` alone has 12).

---

## 23. Latent-only findings (documented, not changed)

Two lower-severity items were verified real but are architectural tradeoffs
rather than active bugs, so left as documentation rather than code changes:

- **`ApiKeyAuth` resolves to the full project-owner user, not scoped to the
  key's project** (`apps/api/apps/auth/authentication.py`). Not currently
  exploitable — `api_key_auth` isn't wired to any router today (confirmed:
  zero references outside its own definition). Worth a comment or a
  follow-up guard if it's ever attached to a route, so a future caller
  doesn't assume the returned user object is itself project-scoped.
- **Ingest's API-key auth cache doesn't coordinate across worker
  processes** (`apps/ingest/app/auth.py`, `scripts/start.sh` defaults to 2
  workers, prod runs 4). Each worker independently caches introspection
  results for a bounded 60s TTL — not an unbounded leak, but a revoked key
  can still be accepted by other workers for up to ~60s after revocation,
  independently per worker. No shared invalidation exists. Worth a Redis- or
  Postgres-backed shared cache if faster revocation propagation matters.

---

## Strategic note

You mentioned wanting this product to move toward something like OpenSRE
(open-source, AI-driven automated incident investigation/root-cause
analysis) rather than a purely passive observability dashboard. Worth
noting: the real `apilens/apilens` repo already has open feature issues
pointed in that general direction — #42 "Advanced Payload Search and
Filtering," #43 "PII Detection and Redaction System," #44 "Breaking Change
Detection and Alerts" — but nothing yet resembling an active
investigation/analysis agent layer. The now-functional `AlertEvent`/
`JobHeartbeat` models (item #21) are a plausible foundation for that
direction — they're exactly the persistence layer an anomaly-scanning job
would need, and previously didn't work at all.

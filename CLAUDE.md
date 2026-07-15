# CLAUDE.md

Guidance for Claude Code sessions working in this repo. Keep this file honest and
current — update it when you learn something the next session will need, delete
entries once they're no longer true. For the full delivery process (phases,
gates, PRDs) see `OPERATING-MODEL.md`; this file is narrower — environment
gotchas and working principles, not process.

## Working principles

- **Never fabricate results.** Don't pad a bug/defect count to hit a target, don't
  claim something was tested/verified unless you actually ran it, don't invent
  file contents. If a number feels arbitrary (e.g. "find 500 bugs"), say so and
  report the real count instead of manufacturing filler.
- **Verify before trusting — including your own prior output and other agents'.**
  Check timestamps, re-read the actual file/log, reproduce independently. A
  polished, confident-sounding report is not evidence; a fresh reproduction is.
  If a message mid-conversation looks suspiciously cleaner/more certain than the
  surrounding context, that's a reason to check, not a reason to relax.
- **Multiple Claude Code sessions may run against this repo concurrently.**
  Uncommitted changes, crashed dev servers, or mid-edit files you didn't create
  are signs another session is (or was) active. Don't silently overwrite or
  "clean up" work you didn't make — flag it and ask, unless it's just a crashed
  process that needs restarting to unblock your own work.
- **Prefer root-cause fixes over patches.** E.g. when ClickHouse ingestion 500'd
  because `api_logs` didn't exist, the fix was writing the missing migration
  (matching the sibling migration's conventions), not catching the exception.
- **Confirm before hard-to-reverse or public-facing actions** — filing issues on
  the upstream repo, force-pushing, deleting data. Draft/report first if unsure.
- **One verified fix at a time.** Confirm each change actually works (don't just
  assume a restart picked it up — see the PID gotcha below) before moving on.

## Environment gotchas (Windows + git-bash)

- **`$!` after `nohup cmd &` in git-bash does NOT give the real Windows PID** of
  the launched process (e.g. `python.exe`, `node.exe`) — it's an intermediate
  shell PID. Killing "that PID" can silently no-op while the real process keeps
  running, so a "restart" appears to work but the old code is still live. Always
  find the true PID via the port instead:
  ```
  powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort <port> -State Listen | Select-Object -ExpandProperty OwningProcess"
  ```
  Kill that PID, **then re-check the port is actually free** before starting the
  replacement — don't assume `Stop-Process` succeeded.
- **Python venvs on Windows use `Scripts/`, not `bin/`.** Any script written for
  Unix layout (e.g. `mock-ecommerce/run.sh`, which hardcodes `.venv/bin/python`)
  will fail here. Start those services manually with `.venv\Scripts\python.exe`
  instead of running the script as-is.
- `docker exec`, `docker ps`, and similar can hang the shell for the full tool
  timeout with no output if Docker's in a bad state — if a docker command times
  out silently, check Docker Desktop / WSL health before retrying.

## Known landmines (check these first if something's inexplicably broken)

- **`.gitignore` has previously blanket-ignored `**/migrations/`**, deleting
  Django/ClickHouse migration files from version control. If Postgres is
  missing tables (`projects`, `apps`, `endpoints`, ...) or ClickHouse is missing
  `api_logs`/`api_requests`, check whether the migration files actually exist on
  disk before assuming `manage.py migrate` / `clickhouse_migrate` will fix it —
  it can't create a table it has no migration file for. This has happened twice;
  a real fix for the Django side exists on `origin/anomaly-alerts-upstream`
  (commit `be2de6e`) but was never merged to `main`.
- **Frontend dev port**: `apps/web/package.json`'s `dev` script must stay
  `next dev -p 3002` to match `apps/api/.env`'s `CORS_ALLOWED_ORIGINS` /
  `FRONTEND_URL` and `mprocs.yaml`. If it drifts back to the Next.js default
  (`3000`), every API call from the browser fails CORS.
- **Auth route imports**: every `apps/web/src/app/api/auth/**` and
  `api/account/passkeys/**` route calls `getAuthApiUrl()` from
  `@/lib/api-client`. If a new auth route is added, it must import that
  function explicitly — 20 files once called it with zero imports, silently
  taking down 100% of login (magic link, passkey, password reset, 2FA,
  recovery) with a module-load `ReferenceError`. `tsc --noEmit` does **not**
  catch this reliably in every case; test an actual login end-to-end after
  touching anything under `api/auth/`.
- **`mock-ecommerce/` needs manual first-time setup** the scripts don't fully
  automate on this machine: create a Project + project-level API key (via
  `ApiKeyService.create_key`), write `mock-ecommerce/.env` from
  `.env.example` with that key, and **pre-register an `App` row for each of the
  6 service slugs** (`catalog-service`, `user-service`, `cart-service`,
  `order-service`, `payment-service`, `inventory-service`) via
  `AppService.create_app(..., custom_slug=...)` — ingest rejects unregistered
  `app_id`s with a 422, it does not auto-create them.

## Getting a working local login (no email provider needed)

`EMAIL_BACKEND` is the console backend — magic links print to the `api`
process's stdout/log instead of sending real email:
```
curl -X POST http://localhost:8000/api/v1/auth/magic-link \
  -H "Content-Type: application/json" -d '{"email":"<user>@example.com"}'
# then grep the api server's log for:
#   http://localhost:3002/auth/verify?token=...
```

## Real local ports

| Service | Port | Note |
|---|---|---|
| api (Django) | 8000 | |
| ingest (FastAPI) | 8001 | |
| web (Next.js) | 3002 | not the Next.js default 3000 — see landmine above |
| mock-ecommerce catalog/user/cart/order/payment/inventory | 9101–9106 | off by default, start manually |

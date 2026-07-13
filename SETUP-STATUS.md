# APILens — Setup Complete ✅ (July 14, 2026)

**All development infrastructure is ready and tested.** Docker containers are running, databases are initialized, and migrations are applied.

## Final Status

| Component | Status | Detail |
|-----------|--------|--------|
| Node.js | ✅ | v24.18.0 |
| pnpm | ✅ | v9.15.9 (global) |
| Python 3.13 | ✅ | Installed via winget |
| Docker Desktop | ✅ | v4.81.0 running + engine online |
| WSL 2 | ✅ | Running with docker-desktop kernel |
| HypervisorPlatform | ✅ | Enabled + active |
| JS/TS deps | ✅ | 627 packages ready |
| Python venv | ✅ | `apps/api/.venv` — 83 packages installed |
| `.env` files | ✅ | Both apps/api and apps/web configured |
| **Docker Containers** | ✅ | **All running (healthy)** |
| **Database Migrations** | ✅ | **Django (19) + ClickHouse applied** |
| **Playwright MCP** | ✅ | **Installed + configured for Claude Code** |

## Current State

### Running Services
- **Postgres** (localhost:5432) — User: `apilens` / DB: `apilens`
- **ClickHouse** (localhost:8123) — DB: `apilens`
- **Redis** (localhost:6379)
- **OPA** (localhost:8181)

### Database Status
- ✅ Django: 19 migrations applied to Postgres
- ✅ ClickHouse: Initialized and ready
- ✅ All tables created and schema validated

## Ready to Launch

To start the development stack:
```powershell
cd C:\Users\remoteadmin\apilens
pnpm dev
```

### Services Available
| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3002 |
| **API** | http://localhost:8000 |
| **Ingest** | http://localhost:8001 |

## Common Commands (from `C:\Users\remoteadmin\apilens`)

```powershell
pnpm dev          # start full stack (mprocs)
pnpm db:up        # start DB containers only
pnpm db:down      # stop DB containers
pnpm db:logs      # tail DB logs
pnpm build        # production build
```

## Backend-only commands (from `apps\api`)

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py clickhouse_migrate
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py runserver
```

## Repo location
`C:\Users\remoteadmin\apilens`

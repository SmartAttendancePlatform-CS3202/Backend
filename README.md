# Smart Attendance Platform — Backend

PID 12 / Group 24 — Smart Attendance and Classroom Access Platform with
Face Verification and Geofenced Check-In.

Three FastAPI microservices sharing one Python package (`libs/shared-core`)
for auth/RBAC/config/schemas, in one repo. Kept separate from the
`web-dashboard` and `mobile-app` repos since those are different
language ecosystems (TypeScript vs Python) — see the root of each
repo for why this split.

```
backend/
├── libs/shared-core/        # shared auth (JWT + RBAC), config, DB client, Pydantic schemas
└── services/
    ├── scheduling-service/  # courses, offerings, timetables
    ├── attendance-service/  # sessions, check-ins, geofence orchestration, reports
    └── ai-vision-service/   # face embedding + matching (internal-only)
```

## Why these three, and not more

- **scheduling-service** and **attendance-service** are separate
  because they're different write patterns: reference data
  (courses/timetables, low write volume) vs. transactional data
  (check-ins, high write volume in short bursts during class time).
- **ai-vision-service** is separate because it has genuinely different
  dependencies (a face-matching library) and a different compute
  profile (CPU-heavy) from the other two.
- There's deliberately no `auth-service` — Supabase Auth already is
  the identity service; `shared-core/auth` just verifies its JWTs.
- There's deliberately no `notification-service` — it's a function
  call inside attendance-service, not its own deployable.

## Local setup

Requires Docker and Docker Compose.

```bash
cp .env.example services/scheduling-service/.env
cp .env.example services/attendance-service/.env
cp .env.example services/ai-vision-service/.env
# fill in each .env with your Supabase project's values
# (attendance-service's .env also needs SCHEDULING_SERVICE_URL / AI_VISION_SERVICE_URL,
#  already defaulted correctly for docker-compose in the compose file)

make up
```

This starts all three services with live-reload:
- scheduling-service → http://localhost:8001
- attendance-service → http://localhost:8002
- ai-vision-service → http://localhost:8003

Each has interactive API docs at `/docs` once running.

Run tests: `make test`. Apply migrations: `make migrate`. Tear down: `make down`.

## Database

The schema all three services share lives in this repo's sibling
document `university_attendance_schema.sql` (from your project chat) —
apply it to your Supabase project's SQL editor, or wire it into
Alembic migrations under each service's `migrations/` folder.

## Working without Docker

Each service can also run standalone:

```bash
cd services/scheduling-service
pip install ../../libs/shared-core
pip install -e .
uvicorn app.main:app --reload --port 8001
```

## Deploying

Each service deploys independently to Render or Railway:

1. Connect this repo, set the service's **root/build context to the
   repo root** (not the service subfolder) — the Dockerfiles need to
   reach `libs/shared-core` during build.
2. Point the Dockerfile path at `services/<name>/Dockerfile`.
3. Set that service's environment variables from its `.env.example`.
4. Copy the platform's deploy-hook URL into this repo's GitHub
   secrets (e.g. `RENDER_SCHEDULING_SERVICE_DEPLOY_HOOK`) — the
   path-filtered workflow in `.github/workflows/` will then only
   redeploy that service when its folder actually changes.
5. For `attendance-service`, set `SCHEDULING_SERVICE_URL` and
   `AI_VISION_SERVICE_URL` to the other two services' deployed URLs.

## Team ownership

A natural 3-way split for a 3-person team:

| Service | Domain |
|---|---|
| `scheduling-service` | Reference data — courses, timetables |
| `attendance-service` | Transactional core — sessions, check-ins, reports |
| `ai-vision-service` | Face verification — different skillset/interest area |


# 1. Create a virtual environment named 'venv'
python -m venv venv

# 2. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 3. Re-install your project (this time it will install inside the venv)
pip install -e .

# 4. Now uvicorn will work perfectly
uvicorn app.main:app --reload --port 8001

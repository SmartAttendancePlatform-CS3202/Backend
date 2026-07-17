# scheduling-service

FastAPI service for course, offering, and timetable management —
part of the Smart Attendance and Classroom Access Platform (PID 12 / Group 24).

Owns: `courses`, `course_offerings`, `enrollments` from the shared schema.

## Local setup

```bash
cp .env.example .env   # fill in your Supabase project's values
pip install ../../libs/shared-core
pip install -e .
uvicorn app.main:app --reload --port 8001
```

Or run it as part of the full stack — see the root `README.md` and
`docker-compose.yml` in this repo.

## Endpoints

- `GET /health` — liveness check
- `GET /me` — decodes the caller's Supabase JWT, confirms auth is wired up
- `GET /courses` — list courses
- `POST /courses` — create a course (admin only)
- `GET /courses/{id}/offerings` — offerings for a course
- `GET /timetables/me` — the calling student's enrolled offerings

## Deploying

Deployed independently via Render/Railway, pointed at this folder's
`Dockerfile` with build context set to the **repo root** (it needs to
reach `libs/shared-core`). See the root README for the full deploy
walkthrough.

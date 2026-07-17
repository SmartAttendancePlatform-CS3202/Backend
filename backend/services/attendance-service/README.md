# attendance-service

FastAPI service handling the actual attendance flow — the core of
PID 12 / Group 24's Smart Attendance and Classroom Access Platform.

Owns: `lecture_sessions`, `verification_windows`, `attendance_records`,
`attendance_verification_attempts` from the shared schema. Calls
`scheduling-service` and `ai-vision-service` internally over HTTP.

## The two-phase check flow this implements

1. **Check-in tick** (`POST /checkin/tick`) — student taps at lecture
   start, location only, no face verification.
2. **Random check** (`POST /checkin/random-check`) — a short window
   opened server-side at an unpredictable point in the lecture;
   requires both face verification (delegated to ai-vision-service)
   and a location check.

A future Wi-Fi-based location method slots in without a schema or API
change — see `verification_method` in the shared schemas.

## Local setup

```bash
cp .env.example .env
pip install ../../libs/shared-core
pip install -e .
uvicorn app.main:app --reload --port 8002
```

## Endpoints

- `GET /health`, `GET /me`
- `POST /sessions` — lecturer starts a lecture session (schedules windows)
- `POST /sessions/{id}/end`
- `POST /checkin/tick` — start-of-lecture location check-in
- `POST /checkin/random-check` — mid-lecture face + location check
- `GET /reports/offerings/{id}` — attendance analytics for one offering

## Deploying

Same pattern as scheduling-service: Docker build context is the repo
root (needs `libs/shared-core`). Set `SCHEDULING_SERVICE_URL` and
`AI_VISION_SERVICE_URL` to the deployed URLs of the other two services.

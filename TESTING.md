# Simple testing guide

## 1. Install dependencies

Use the project Dockerfiles for the complete environment. The local environment must include the packages in the three service `pyproject.toml` files and `libs/shared-core/pyproject.toml`.

## 2. Environment

Copy `.env.example` into each service `.env` and set:

- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- one strong shared `INTERNAL_API_KEY`

Do not commit real secrets.

## 3. Start the stack

```bash
docker compose up --build
```

Public gateway:

```text
http://localhost:8000
```

Scheduling docs:

```text
http://localhost:8000/scheduling/docs
```

Attendance docs:

```text
http://localhost:8000/attendance/docs
```

RabbitMQ UI:

```text
http://localhost:15672
```

## 4. Run automated tests

```bash
pytest -q services/attendance-service/tests/test_geofence.py
pytest -q services/attendance-service/tests
pytest -q services/scheduling-service/tests
pytest -q services/ai-vision-service/tests
```

The full suite requires all project dependencies; the code should first be compiled with:

```bash
python -m compileall -q libs/shared-core/shared_core services/*/app
```

## 5. Manual API flow

1. Obtain a Supabase access token for an active student.
2. Register the student's face through:
   `POST /attendance/onboarding/register-face`
3. Create an offering, venue and enrollment using Scheduling.
4. Start a lecture session:
   `POST /attendance/sessions`
5. Submit a location tick:
   `POST /attendance/checkin/tick`
6. Once the random check is open, retrieve the active window:
   `GET /attendance/checkin/windows/active?lecture_session_id=<id>`
7. Submit the face check:
   `POST /attendance/checkin/random-check`
8. Follow RabbitMQ until AI Vision publishes the result.
9. Read the final record:
   `GET /attendance/attendance/records/<record-id>`

## 6. Security checks

Verify these cases manually:

- no JWT -> 401
- expired/invalid JWT -> 401
- student calling lecturer/admin endpoint -> 403
- lecturer accessing another lecturer's offering -> 403
- client calling AI Vision without `X-Internal-Key` -> 401
- oversized request -> 413
- excessive requests -> 429
- invalid base64 image -> 400
- invalid latitude/longitude -> 422
- student outside circle -> rejected
- student outside square -> rejected
- duplicate tick -> 409

## 7. Failure checks

Stop AI Vision while submitting a random check. The Attendance API should report queue/service failure instead of marking attendance successful.

Stop RabbitMQ. New random-check requests should fail cleanly rather than returning a false `processing` state.

Send the same AI result twice. Attendance must not create two verification attempts for the same `attempt_id`.

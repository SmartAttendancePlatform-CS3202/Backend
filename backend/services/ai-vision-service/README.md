# ai-vision-service

FastAPI service for face embedding extraction and matching —
PID 12 / Group 24's Smart Attendance and Classroom Access Platform.

Owns: `face_profiles` from the shared schema (pgvector embeddings).
Called internally by attendance-service; not exposed to the mobile
app directly — the internal key check in `main.py` enforces that.

## Local setup

```bash
cp .env.example .env
pip install ../../libs/shared-core
pip install -e .
uvicorn app.main:app --reload --port 8003
```

## Picking a face-matching library

`app/services/embedding_service.py` is intentionally left as a stub —
that's the one file whose implementation depends on which library you
settle on:

- **DeepFace** (`pip install deepface`) — easiest to start with,
  wraps several models (ArcFace, Facenet512, etc.), decent accuracy
  out of the box.
- **face_recognition** (`pip install face_recognition`) — dlib-based,
  128-d embeddings, lighter weight, needs `cmake`/`dlib` build tools.

Whichever you pick, keep the embedding dimension in sync with the
`vector(512)` column in `university_attendance_schema.sql` — 128-d
models will need that column resized to `vector(128)`.

## Endpoints

- `GET /health` — no auth (used for container health checks)
- `POST /verify` — internal only, called by attendance-service
- `POST /register` — internal only, called during mobile onboarding

## Deploying

Same Docker-build-context-at-repo-root pattern as the other two
services. Face-matching libraries can be heavy — if your Render/Railway
free tier struggles with image size or cold-start time, that's the
concrete case for this service living on its own deploy target
separate from the other two.

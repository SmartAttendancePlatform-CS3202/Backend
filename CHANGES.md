# Backend revision changes

## Core architecture
- Kept the existing single Supabase PostgreSQL database and existing tables.
- Kept `reference_photo_url` as a deliberate fake placeholder; raw face photos are not stored.
- AI Vision only owns face embedding registration/verification and no longer writes attendance records directly.
- Attendance owns the final attendance decision and consumes AI verification results from RabbitMQ.
- Added correlation/attempt IDs to make the async flow idempotent.

## Attendance
- Fixed session lifecycle to create an active session and verification windows.
- Fixed the `check_in` enum mismatch with the existing database enum.
- Implemented real geofence verification for:
  - circle: center + radius
  - square: four vertices stored using the existing DB `polygon` enum / JSON boundary representation
- Added server-side enrollment checks, duplicate check-in prevention, late classification, session finalization, absent/flagged handling and lecturer resource authorization.
- Added attendance record lookup and CSV export.

## RabbitMQ
- Added durable face-verification request/result queues.
- Added Attendance result consumer.
- Added ACK handling, retry handling and a dead-letter queue after repeated AI failures.
- Queue/publish failures now return an explicit 503 instead of falsely reporting success.

## AI Vision
- Fixed broken syntax/imports.
- Added image/base64 validation and a configurable face similarity threshold.
- Face registration stores the embedding only; the fake reference photo URL is retained exactly as a placeholder.
- AI inference runs outside the event loop using a worker thread.

## Security
- JWT validation with expiry/audience/sub checks.
- RBAC.
- Resource-level authorization for lecturer-owned offerings/sessions/enrollments/attendance.
- Separate internal service key for service-to-service endpoints.
- Request-size and per-instance rate limiting fallback.
- Base64/image validation and coordinate validation.
- Restrictive CORS from `ALLOWED_ORIGINS`.
- Environment-only secrets; real credentials were removed from `.env.example` files.
- Audit logging hooks for attendance overrides, venue changes and user role/status changes.
- HTTPS-ready gateway/deployment configuration.

## API gateway / deployment
- Added Kong declarative configuration for `/scheduling/*` and `/attendance/*`.
- AI Vision has no public Kong route and no published Docker port.
- Updated Kubernetes ingress so AI Vision is internal-only and HTTPS is enforced externally.
- Added `k8s/secrets.example.yaml` for deployment secrets.

## Tests
- Added geofence unit tests for circle, square/polygon and invalid coordinates.
- Added configuration/secrets sanity checks.
- Added pytest path setup for each service.
- Added compile and YAML validation checks to the release validation steps below.

## Intentionally not changed
- LMS/course-content tables and their backend behavior were left alone.
- No new database schema isolation was introduced.

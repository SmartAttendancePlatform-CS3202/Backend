# Smart Attendance Backend — working revision

This revision keeps the existing single Supabase PostgreSQL database and existing tables. No LMS-content tables were changed.

## Services
- scheduling-service: courses, offerings, venues, enrollments, timetables, user/profile operations
- attendance-service: sessions, circle/square geofencing, check-in, attendance state, reports, audit-safe overrides
- ai-vision-service: face embedding registration + verification; never writes attendance records
- RabbitMQ: asynchronous face-verification request/result flow
- Kong: optional/default API gateway for `/scheduling/*` and `/attendance/*`; AI Vision has no public gateway route

## Face registration
The mobile app sends a face image only for embedding extraction. The backend stores the 512-D embedding. Raw images are not stored. `reference_photo_url` remains a deliberate fake placeholder for now and is not used to retrieve an image.

## Geofencing
`venues.boundary_data` supports:
- circle: `{ "center": {"lat": ..., "lng": ...}, "radius_m": 30 }`
- square: stored with the existing DB `polygon` enum and four vertices/points in JSON, e.g. `{ "points": [[lat,lng], ...] }`

The attendance service performs a point-in-polygon check for square/polygon boundaries and Haversine distance for circles.

## Security included
JWT validation, RBAC, resource-level ownership checks, internal service authentication, request-size validation, face-image/base64 validation, SQLAlchemy parameterized queries, audit logging hooks, restrictive CORS, environment-only secrets, HTTPS-ready deployment, and Kong rate limiting. A per-instance request guard is also present as a fallback.

## Local test
1. Copy env examples to each service `.env` and set real Supabase database/JWT settings plus one strong `INTERNAL_API_KEY`.
2. Run `docker compose up --build`.
3. Gateway: `http://localhost:8000`
4. Scheduling docs: `http://localhost:8000/scheduling/docs`
5. Attendance docs: `http://localhost:8000/attendance/docs`
6. RabbitMQ UI: `http://localhost:15672` (`guest` / `guest` for local development)
7. Run unit tests: `pytest services/attendance-service/tests -q`
8. Full Python syntax check: `python -m compileall libs/shared-core/shared_core services/*/app`

## Important operational note
Kong is the local API-gateway option. Do not publish port 8003 for AI Vision. In Kubernetes keep AI Vision ClusterIP/internal-only; the provided NGINX ingress exposes only scheduling and attendance and forces HTTPS. Copy `k8s/secrets.example.yaml` to a real Secret with actual values before deployment.

## End-to-end flow
Student JWT -> attendance tick -> server-side geofence -> AttendanceRecord -> random window -> RabbitMQ -> AI Vision face verification -> RabbitMQ result -> Attendance finalizes the verification attempt and record.

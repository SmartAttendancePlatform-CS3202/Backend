"""Shared OpenAPI / Swagger helpers for the three FastAPI services."""

from __future__ import annotations

from typing import Any

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "persistAuthorization": True,
    "displayRequestDuration": True,
    "filter": True,
    "tryItOutEnabled": True,
    "docExpansion": "list",
}

AUTH_HOWTO = """
## Authentication

Most endpoints require a **Supabase JWT** (role: admin / lecturer / student).

1. Sign in via Supabase Auth and copy the `access_token`.
2. Click **Authorize** in this Swagger UI.
3. Paste the token into **BearerAuth** (no `Bearer ` prefix needed).
4. Call endpoints — locked routes send `Authorization: Bearer <token>`.

Role-gated routes return **403** if the token user's role is not allowed.

### Internal service key (ai-vision only)

`POST /verify` and `POST /register` use **InternalApiKey** (`X-Internal-Key` header).
Set it to the same value as `INTERNAL_API_KEY` in the service `.env`.
"""


def service_description(body: str) -> str:
    return f"{body.strip()}\n\n{AUTH_HOWTO.strip()}\n"


API_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Smart Attendance — API Docs</title>
  <style>
    body {
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      margin: 0; min-height: 100vh;
      background: linear-gradient(160deg, #0f172a 0%, #1e3a5f 45%, #0c4a6e 100%);
      color: #e2e8f0;
      display: flex; align-items: center; justify-content: center;
      padding: 2rem;
    }
    main {
      max-width: 40rem; width: 100%;
      background: rgba(15, 23, 42, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.25);
      border-radius: 12px; padding: 2rem 2.25rem;
    }
    h1 { margin: 0 0 0.35rem; font-size: 1.6rem; }
    p { margin: 0 0 1.5rem; color: #94a3b8; line-height: 1.5; }
    ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.75rem; }
    a {
      display: block; text-decoration: none; color: #f8fafc;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 8px; padding: 0.9rem 1.1rem;
    }
    a:hover { background: rgba(56, 189, 248, 0.22); border-color: #38bdf8; }
    strong { display: block; font-size: 1.05rem; margin-bottom: 0.2rem; }
    span { color: #7dd3fc; font-size: 0.85rem; }
  </style>
</head>
<body>
  <main>
    <h1>Smart Attendance API</h1>
    <p>Interactive Swagger UI for each microservice. Use <em>Authorize</em> with a Supabase JWT (or InternalApiKey for vision).</p>
    <ul>
      <li>
        <a href="http://localhost:8001/docs">
          <strong>Scheduling Service</strong>
          <span>localhost:8001/docs — courses, offerings, timetables</span>
        </a>
      </li>
      <li>
        <a href="http://localhost:8002/docs">
          <strong>Attendance Service</strong>
          <span>localhost:8002/docs — sessions, check-in, reports</span>
        </a>
      </li>
      <li>
        <a href="http://localhost:8003/docs">
          <strong>AI Vision Service</strong>
          <span>localhost:8003/docs — face register / verify</span>
        </a>
      </li>
    </ul>
  </main>
</body>
</html>
"""

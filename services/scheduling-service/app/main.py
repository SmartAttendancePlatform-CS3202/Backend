from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from prometheus_fastapi_instrumentator import Instrumentator

from shared_core.auth.jwt import get_current_user
from shared_core.models.identity import User
from shared_core.openapi import API_INDEX_HTML, SWAGGER_UI_PARAMETERS, service_description

from app.routers import (
    courses,
    timetables,
    users,
    departments,
    academic_years,
    offerings,
    venues,
    enrollments,
)

OPENAPI_TAGS = [
    {"name": "users", "description": "User / student / lecturer profiles and roles"},
    {"name": "departments", "description": "Department CRUD"},
    {"name": "academic-years", "description": "Academic year reference data"},
    {"name": "courses", "description": "Course catalog and related offerings"},
    {"name": "offerings", "description": "Course offerings per term and enrolled students"},
    {"name": "venues", "description": "Lecture venues / rooms (with geofence coords)"},
    {"name": "enrollments", "description": "Student enrollments into offerings"},
    {"name": "timetables", "description": "Student and lecturer personal timetables"},
    {"name": "health", "description": "Service health"},
]

app = FastAPI(
    title="Scheduling Service",
    version="1.0.0",
    description=service_description(
        """
Reference-data API for the Smart Attendance platform: users, departments,
academic years, courses, offerings, venues, enrollments, and timetables.

**Local base URL:** `http://localhost:8001`  
**Swagger:** `/docs` · **ReDoc:** `/redoc` · **OpenAPI JSON:** `/openapi.json`
"""
    ),
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    contact={
        "name": "Smart Attendance Platform",
        "url": "https://github.com/SmartAttendancePlatform-CS3202/Backend",
    },
)

Instrumentator().instrument(app).expose(app)

app.include_router(users.router)
app.include_router(departments.router)
app.include_router(academic_years.router)
app.include_router(courses.router)
app.include_router(offerings.router)
app.include_router(venues.router)
app.include_router(enrollments.router)
app.include_router(timetables.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def api_index():
    """Landing page with links to all three services' Swagger UIs."""
    return API_INDEX_HTML


@app.get("/health", tags=["health"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "scheduling-service"}


@app.get("/me", tags=["users"], summary="Current authenticated user")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}

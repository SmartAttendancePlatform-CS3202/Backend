from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from shared_core.auth.jwt import get_current_user
from shared_core.db.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
from shared_core.models.identity import User
from shared_core.openapi import API_INDEX_HTML, SWAGGER_UI_PARAMETERS, service_description
from shared_core.logging import setup_logging
from shared_core.middleware import StructlogMiddleware

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

setup_logging("scheduling-service")

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

app.add_middleware(StructlogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/admin/health", tags=["health"], summary="Deep health check with DB connectivity")
def admin_health(db: Session = Depends(get_db)):
    start_time = time.time()
    status = "healthy"
    try:
        # Check DB connectivity
        db.execute(text("SELECT 1"))
    except Exception as e:
        status = "degraded"
        
    latency_ms = int((time.time() - start_time) * 1000)
    
    return {
        "name": "Scheduling Service",
        "port": 8001,
        "status": status,
        "latency_ms": latency_ms,
        "endpoint": "/admin/health",
        "version": "1.0.0"
    }


@app.get("/me", tags=["users"], summary="Current authenticated user")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}

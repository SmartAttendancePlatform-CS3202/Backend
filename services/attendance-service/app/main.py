from contextlib import asynccontextmanager

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
    sessions,
    checkin,
    reports,
    attendance,
    onboarding,
    notifications,
    alerts,
)
from app.rabbitmq.publisher import init_rabbitmq, close_rabbitmq

OPENAPI_TAGS = [
    {"name": "sessions", "description": "Lecture session lifecycle (start, end, live status)"},
    {"name": "checkin", "description": "Student geofenced ticks and random face checks"},
    {"name": "attendance", "description": "Attendance records, overrides, and verification attempts"},
    {"name": "reports", "description": "Offering / student attendance reports and trends"},
    {"name": "onboarding", "description": "Student face enrollment via ai-vision"},
    {"name": "notifications", "description": "User notifications and lecturer broadcasts"},
    {"name": "alerts", "description": "Fraud / anomaly alerts for staff"},
    {"name": "users", "description": "Current authenticated user helper"},
    {"name": "health", "description": "Service health"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_rabbitmq()
    yield
    await close_rabbitmq()

setup_logging("attendance-service")

app = FastAPI(
    title="Attendance Service",
    version="1.0.0",
    description=service_description(
        """
Transactional attendance API: sessions, geofenced check-in, face-verification
orchestration, reports, notifications, and alerts.

**Local base URL:** `http://localhost:8002`  
**Swagger:** `/docs` · **ReDoc:** `/redoc` · **OpenAPI JSON:** `/openapi.json`

Calls scheduling (`SCHEDULING_SERVICE_URL`) and ai-vision (`AI_VISION_SERVICE_URL`) as needed.
"""
    ),
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    lifespan=lifespan,
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

app.include_router(sessions.router)
app.include_router(checkin.router)
app.include_router(reports.router)
app.include_router(attendance.router)
app.include_router(onboarding.router)
app.include_router(notifications.router)
app.include_router(alerts.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def api_index():
    return API_INDEX_HTML


@app.get("/health", tags=["health"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "attendance-service"}


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
        "name": "Attendance Service",
        "port": 8002,
        "status": status,
        "latency_ms": latency_ms,
        "endpoint": "/admin/health",
        "version": "1.0.0"
    }


@app.get("/me", tags=["users"], summary="Current authenticated user")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}

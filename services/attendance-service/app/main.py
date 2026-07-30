from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from shared_core.auth.jwt import get_current_user
from shared_core.models.identity import User

from app.routers import (
    sessions, checkin, reports, attendance, 
    onboarding, notifications, alerts
)
from app.rabbitmq.publisher import init_rabbitmq, close_rabbitmq

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_rabbitmq()
    yield
    # Shutdown
    await close_rabbitmq()

app = FastAPI(title="Attendance Service", lifespan=lifespan)

app.include_router(sessions.router)
app.include_router(checkin.router)
app.include_router(reports.router)
app.include_router(attendance.router)
app.include_router(onboarding.router)
app.include_router(notifications.router)
app.include_router(alerts.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "attendance-service"}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}

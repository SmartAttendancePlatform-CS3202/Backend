from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
from sqlalchemy import text
from shared_core.auth.jwt import get_current_user
from shared_core.db.session import get_db
from shared_core.models.identity import User
from shared_core.openapi import API_INDEX_HTML, SWAGGER_UI_PARAMETERS, service_description
from shared_core.logging import setup_logging
from shared_core.middleware import RequestGuardMiddleware, StructlogMiddleware
from shared_core.config import get_settings
from app.routers import sessions, checkin, reports, attendance, onboarding, notifications, alerts
from app.rabbitmq.publisher import init_rabbitmq, close_rabbitmq
from app.rabbitmq.result_consumer import start_result_consumer, stop_result_consumer

setup_logging("attendance-service")

@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_rabbitmq()
    await start_result_consumer()
    yield
    await stop_result_consumer()
    await close_rabbitmq()

app=FastAPI(title="Attendance Service",version="2.0.0",description=service_description("Attendance, geofenced check-in, AI verification orchestration and reporting."),swagger_ui_parameters=SWAGGER_UI_PARAMETERS,lifespan=lifespan,root_path="/attendance")
app.add_middleware(RequestGuardMiddleware)
app.add_middleware(StructlogMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=get_settings().allowed_origin_list,allow_credentials=True,allow_methods=["GET","POST","PATCH","OPTIONS"],allow_headers=["Authorization","Content-Type","X-Request-ID"])
Instrumentator().instrument(app).expose(app)
for router in (sessions.router,checkin.router,reports.router,attendance.router,onboarding.router,notifications.router,alerts.router): app.include_router(router)

@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def root(): return API_INDEX_HTML

@app.get("/health")
def health(): return {"status":"ok","service":"attendance-service"}

@app.get("/admin/health")
def admin_health(db:Session=Depends(get_db)):
    try: db.execute(text("SELECT 1")); db_ok=True
    except Exception: db_ok=False
    return {"service":"attendance-service","status":"healthy" if db_ok else "degraded","database":db_ok}

@app.get("/me")
def me(user:User=Depends(get_current_user)): return {"user_id":user.id,"role":user.role}

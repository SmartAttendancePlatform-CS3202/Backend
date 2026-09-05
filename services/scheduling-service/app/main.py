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
from shared_core.telemetry import setup_telemetry, instrument_app
setup_telemetry("scheduling-service") 
from .routers import (
    academic_years,
    admin,
    courses,
    departments,
    enrollments,
    offerings,
    timetables,
    users,
    venues,
)
setup_logging("scheduling-service")
app=FastAPI(title="Scheduling Service",version="2.0.0",description=service_description("Scheduling, courses, offerings, venues, enrollment and timetable API."),swagger_ui_parameters=SWAGGER_UI_PARAMETERS,root_path="/scheduling")
app.add_middleware(RequestGuardMiddleware); app.add_middleware(StructlogMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=get_settings().allowed_origin_list,allow_credentials=True,allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type","X-Internal-Key","X-Request-ID"])
Instrumentator().instrument(app).expose(app)
instrument_app(app)
for router in (users.router,departments.router,academic_years.router,courses.router,offerings.router,venues.router,enrollments.router,timetables.router,admin.router): app.include_router(router)
@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def root(): return API_INDEX_HTML
@app.get("/health")
def health(): return {"status":"ok","service":"scheduling-service"}
@app.get("/admin/health")
def admin_health(db:Session=Depends(get_db)):
    try: db.execute(text("SELECT 1")); db_ok=True
    except Exception: db_ok=False
    return {"service":"scheduling-service","status":"healthy" if db_ok else "degraded","database":db_ok}
@app.get("/me")
def me(user:User=Depends(get_current_user)): return {"user_id":user.id,"role":user.role}

from fastapi import Depends, FastAPI

from shared_core.auth.jwt import get_current_user

from app.routers import checkin, reports, sessions

app = FastAPI(title="Attendance Service")

app.include_router(sessions.router)
app.include_router(checkin.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "attendance-service"}


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user.get("sub"), "role": user.get("role")}

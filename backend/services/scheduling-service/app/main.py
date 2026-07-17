from fastapi import Depends, FastAPI

from shared_core.auth.jwt import get_current_user

from app.routers import courses, timetables

app = FastAPI(title="Scheduling Service")

app.include_router(courses.router)
app.include_router(timetables.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduling-service"}


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user.get("sub"), "role": user.get("role")}

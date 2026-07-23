from fastapi import Depends, FastAPI

from shared_core.auth.jwt import get_current_user
from shared_core.models.identity import User

from app.routers import (
    courses, timetables, users, departments, 
    academic_years, offerings, venues, enrollments
)

app = FastAPI(title="Scheduling Service")

app.include_router(users.router)
app.include_router(departments.router)
app.include_router(academic_years.router)
app.include_router(courses.router)
app.include_router(offerings.router)
app.include_router(venues.router)
app.include_router(enrollments.router)
app.include_router(timetables.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduling-service"}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}


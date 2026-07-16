from uuid import UUID

from fastapi import APIRouter, Depends

from shared_core.auth.rbac import require_role
from shared_core.schemas.course import CourseOfferingOut, CourseOut

from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
def list_courses():
    return course_service.list_courses()


@router.post("", response_model=CourseOut, dependencies=[Depends(require_role("admin"))])
def create_course(course: CourseOut):
    return course_service.create_course(course)


@router.get("/{course_id}/offerings", response_model=list[CourseOfferingOut])
def list_offerings(course_id: UUID):
    return course_service.list_offerings(course_id)

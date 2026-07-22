from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.course import CourseOut, CourseCreate, CourseUpdate, CourseOfferingOut
from shared_core.models.identity import User
from app.services import course_service, offering_service

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("", response_model=List[CourseOut])
def list_courses(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return course_service.get_all_courses(db, skip=skip, limit=limit)

@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    data: CourseCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return course_service.create_course(db, data.model_dump())

@router.get("/{id}", response_model=CourseOut)
def get_course(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = course_service.get_course(db, id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.patch("/{id}", response_model=CourseOut)
def update_course(
    id: UUID,
    data: CourseUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    course = course_service.update_course(db, id, data.model_dump(exclude_unset=True))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.get("/{id}/offerings", response_model=List[CourseOfferingOut])
def list_offerings_for_course(
    id: UUID,
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return offering_service.get_offerings_by_course(db, id, skip=skip, limit=limit)

@router.get("/offerings/{id}", response_model=CourseOfferingOut)
def get_offering_by_id(
    id: UUID,
    db: Session = Depends(get_db)
):
    # This is for internal service-to-service calls (like from attendance-service)
    offering = offering_service.get_offering(db, id)
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    return offering

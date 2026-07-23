from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.course import CourseOfferingOut, CourseOfferingCreate, CourseOfferingUpdate
from shared_core.schemas.identity import StudentOut
from shared_core.models.identity import User
from app.services import offering_service, enrollment_service

router = APIRouter(prefix="/offerings", tags=["offerings"])

@router.get("", response_model=List[CourseOfferingOut])
def list_offerings(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return offering_service.get_all_offerings(db, skip=skip, limit=limit)

@router.post("", response_model=CourseOfferingOut, status_code=status.HTTP_201_CREATED)
def create_offering(
    data: CourseOfferingCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return offering_service.create_offering(db, data.model_dump(), current_user.id)

@router.get("/{id}", response_model=CourseOfferingOut)
def get_offering(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    offering = offering_service.get_offering(db, id)
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    return offering

@router.patch("/{id}", response_model=CourseOfferingOut)
def update_offering(
    id: UUID,
    data: CourseOfferingUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    offering = offering_service.update_offering(db, id, data.model_dump(exclude_unset=True))
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    return offering

@router.get("/{id}/students", response_model=List[StudentOut])
def get_enrolled_students(
    id: UUID,
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return enrollment_service.get_students_for_offering(db, id, skip=skip, limit=limit)

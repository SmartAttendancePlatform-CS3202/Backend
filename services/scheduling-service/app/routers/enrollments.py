from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from shared_core.db.session import get_db
from shared_core.auth.rbac import require_role
from shared_core.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from shared_core.models.identity import User
from app.services import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

@router.post("", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    data: EnrollmentCreate,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return enrollment_service.create_enrollment(db, data.student_id, data.course_offering_id, current_user.id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    success = enrollment_service.delete_enrollment(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")

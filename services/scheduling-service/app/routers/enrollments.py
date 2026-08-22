from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from shared_core.db.session import get_db
from shared_core.auth.rbac import require_role
from shared_core.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from shared_core.models.identity import User
from app.services import enrollment_service

router=APIRouter(prefix="/enrollments",tags=["enrollments"])

@router.post("",response_model=EnrollmentOut,status_code=201)
def create(data:EnrollmentCreate,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    return enrollment_service.create_enrollment(db,data.student_id,data.course_offering_id,current_user.id)

@router.get("/{id}",response_model=EnrollmentOut)
def get(id:UUID,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    obj=enrollment_service.get_enrollment(db,id)
    if not obj: raise HTTPException(404,"Enrollment not found")
    if getattr(current_user.role,'value',current_user.role)=='lecturer' and obj.course_offering.lecturer_id != current_user.id: raise HTTPException(403,"Forbidden")
    return obj

@router.delete("/{id}",status_code=204)
def delete(id:UUID,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    if not enrollment_service.delete_enrollment(db,id,current_user.id): raise HTTPException(404,"Enrollment not found")

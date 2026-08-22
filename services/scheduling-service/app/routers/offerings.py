from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role, verify_internal_key
from shared_core.schemas.course import CourseOfferingOut, CourseOfferingCreate, CourseOfferingUpdate
from shared_core.schemas.identity import StudentOut
from shared_core.models.identity import User
from app.services import offering_service, enrollment_service

router=APIRouter(prefix="/offerings",tags=["offerings"])

@router.get("",response_model=List[CourseOfferingOut])
def list_offerings(skip:int=0,limit:int=100,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)): return offering_service.get_all_offerings(db,skip,limit)

@router.post("",response_model=CourseOfferingOut,status_code=201)
def create_offering(data:CourseOfferingCreate,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    payload=data.model_dump()
    if getattr(current_user.role,"value",current_user.role)=="lecturer":
        payload["lecturer_id"]=current_user.id
    return offering_service.create_offering(db,payload,current_user.id)

@router.get("/internal/{id}",dependencies=[Depends(verify_internal_key)],response_model=CourseOfferingOut)
def internal_get(id:UUID,db:Session=Depends(get_db)):
    obj=offering_service.get_offering(db,id)
    if not obj: raise HTTPException(404,"Offering not found")
    return obj

@router.get("/{id}",response_model=CourseOfferingOut)
def get_offering(id:UUID,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    obj=offering_service.get_offering(db,id)
    if not obj: raise HTTPException(404,"Offering not found")
    role=getattr(current_user.role,'value',current_user.role)
    if role=='lecturer' and obj.lecturer_id != current_user.id: raise HTTPException(403,"Forbidden")
    if role=='student' and not any(e.student_id==current_user.id and e.is_active for e in obj.enrollments): raise HTTPException(403,"Forbidden")
    return obj

@router.patch("/{id}",response_model=CourseOfferingOut)
def update(id:UUID,data:CourseOfferingUpdate,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    obj=offering_service.get_offering(db,id)
    if not obj: raise HTTPException(404,"Offering not found")
    if getattr(current_user.role,'value',current_user.role)=='lecturer':
        if obj.lecturer_id != current_user.id: raise HTTPException(403,"Forbidden")
        payload=data.model_dump(exclude_unset=True)
        payload.pop("lecturer_id",None)
    else:
        payload=data.model_dump(exclude_unset=True)
    return offering_service.update_offering(db,id,payload)

@router.get("/{id}/students",response_model=List[StudentOut])
def students(id:UUID,skip:int=0,limit:int=100,current_user:User=Depends(require_role("admin","lecturer")),db:Session=Depends(get_db)):
    obj=offering_service.get_offering(db,id)
    if not obj: raise HTTPException(404,"Offering not found")
    if getattr(current_user.role,'value',current_user.role)=='lecturer' and obj.lecturer_id != current_user.id: raise HTTPException(403,"Forbidden")
    return enrollment_service.get_students_for_offering(db,id,skip,limit)

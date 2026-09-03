from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.notification import NoticeBroadcast
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/me")
def get_my_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.get_my_notices(db, current_user.id)

@router.get("/all")
def get_all_notifications(current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return notification_service.get_all_notices(db)

@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
def broadcast_notification(data: NoticeBroadcast, current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    if getattr(current_user.role, "value", current_user.role) == "lecturer" and data.course_offering_id:
        offering = __import__('shared_core.models.courses', fromlist=['CourseOffering']).CourseOffering
        obj = db.get(offering, data.course_offering_id)
        if not obj or obj.lecturer_id != current_user.id:
            raise HTTPException(403, "You are not assigned to this offering")
    return notification_service.broadcast_notice(db, data.model_dump(), current_user.id)

@router.patch("/{id}/read")
def mark_read(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = notification_service.mark_read(db, id, current_user.id)
    if not result: raise HTTPException(404, "Notification not found")
    return result

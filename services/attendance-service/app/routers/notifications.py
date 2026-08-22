from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.notification import NoticeBroadcast
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/me", response_model=List[dict])
def get_my_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.get_my_notices(db, current_user.id)

@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
def broadcast_notification(data: NoticeBroadcast, current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    return notification_service.broadcast_notice(db, data.model_dump())

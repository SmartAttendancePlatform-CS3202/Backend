from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.notification import AlertOut
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertOut])
def get_alerts(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return alert_service.get_alerts(db, skip=skip, limit=limit)

@router.patch("/{id}/read", response_model=AlertOut)
def mark_alert_read(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    alert = alert_service.mark_read(db, id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

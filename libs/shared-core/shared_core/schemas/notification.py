from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from shared_core.models.enums import NoticeUrgency, UserRole, AlertType

class NoticeBase(BaseModel):
    course_offering_id: Optional[UUID] = None
    title: str
    body: str
    urgency: NoticeUrgency = NoticeUrgency.normal
    expires_at: Optional[datetime] = None
    target_roles: Optional[List[UserRole]] = None
    target_user_ids: Optional[List[UUID]] = None

class NoticeBroadcast(NoticeBase):
    pass

class NoticeOut(NoticeBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AlertOut(BaseModel):
    id: UUID
    title: Optional[str] = None
    type: AlertType
    message: str
    details: Optional[dict] = None
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

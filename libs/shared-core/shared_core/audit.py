from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from shared_core.models.system import AuditLog

def audit(db: Session, user_id: UUID | None, action: str, entity_type: str | None = None, entity_id: UUID | None = None, old_data: dict | None = None, new_data: dict | None = None, ip_address: str | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, old_data=old_data, new_data=new_data, ip_address=ip_address))

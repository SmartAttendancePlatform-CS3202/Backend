from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.system import SystemAlert

def get_alerts(db: Session, skip: int = 0, limit: int = 100) -> List[SystemAlert]:
    return db.query(SystemAlert).offset(skip).limit(limit).all()

def mark_read(db: Session, alert_id: UUID) -> Optional[SystemAlert]:
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert:
        alert.is_read = True
        db.commit()
        db.refresh(alert)
    return alert

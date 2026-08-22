from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from shared_core.models.system import SystemAlert

# Notifications/course notices are intentionally left out of this backend revision.
# The existing LMS-related tables remain unchanged as requested.
def get_notices(db: Session, user_id: UUID) -> List[dict]:
    alerts = db.query(SystemAlert).filter(SystemAlert.is_read.is_(False)).all()
    return [{"id": a.id, "title": a.title, "body": a.message, "created_at": a.created_at} for a in alerts]

def create_notice(db: Session, data: dict) -> dict:
    return {"id": "not-implemented", **data}

from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
# Note: Since there is no explicit Notice model in the provided schema, we might use SystemAlert for now,
# or simply leave this as a stub returning an empty list until the schema is updated.
from shared_core.models.system import SystemAlert

def get_notices(db: Session, user_id: UUID) -> List[dict]:
    # Stub: Return system alerts as notices for now
    alerts = db.query(SystemAlert).filter(SystemAlert.is_read == False).all()
    return [{"id": a.id, "title": a.title, "body": a.message, "created_at": a.created_at} for a in alerts]

def create_notice(db: Session, data: dict) -> dict:
    # Stub
    return {"id": "123e4567-e89b-12d3-a456-426614174000", **data}

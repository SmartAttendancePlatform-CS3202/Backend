from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from shared_core.auth.rbac import require_role
from shared_core.db.session import get_db
from shared_core.models.identity import User, Student, Lecturer
from shared_core.models.courses import Course, CourseOffering
from shared_core.models.attendance import Venue
from shared_core.models.system import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/audit-logs")
def audit_logs(skip: int = 0, limit: int = 100, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(min(limit, 200)).all()
    out = []
    for row in rows:
        actor = row.user
        role = getattr(actor.role, "value", actor.role) if actor else "system"
        out.append({
            "id": str(row.id),
            "action": row.action,
            "category": (row.entity_type or "system").split(".")[0],
            "performed_by_id": str(row.user_id) if row.user_id else None,
            "performed_by_name": getattr(getattr(actor, "student_profile", None), "display_name", None) or getattr(getattr(actor, "lecturer_profile", None), "email", None) or (actor.username if actor else "SYSTEM"),
            "performed_by_role": role,
            "details": str(row.new_data or row.old_data or {}),
            "timestamp": row.created_at,
            "severity": "critical" if "security" in row.action.lower() else "info",
            "ip_address": str(row.ip_address) if row.ip_address else None,
        })
    return out

@router.get("/stats")
def stats(current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return {
        "total_students": db.query(func.count(Student.id)).scalar() or 0,
        "total_lecturers": db.query(func.count(Lecturer.id)).scalar() or 0,
        "total_courses": db.query(func.count(Course.id)).scalar() or 0,
        "total_offerings": db.query(func.count(CourseOffering.id)).scalar() or 0,
        "total_venues": db.query(func.count(Venue.id)).scalar() or 0,
    }

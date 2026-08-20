from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from shared_core.models.identity import User, Student, Lecturer
from shared_core.models.enums import UserRole, UserStatus

def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def list_users(
    db: Session,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """List users with their student/lecturer profile + department eager-loaded,
    so the service layer can flatten them without extra queries per row."""
    query = db.query(User).options(
        joinedload(User.student_profile).joinedload(Student.department),
        joinedload(User.lecturer_profile).joinedload(Lecturer.department),
    )
    if role is not None:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
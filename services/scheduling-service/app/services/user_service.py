from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories import user_repository
from shared_core.models.enums import UserRole, UserStatus
from shared_core.schemas.identity import UserDirectoryOut

def get_user(db: Session, user_id: UUID):
    return user_repository.get_user(db, user_id=user_id)

def list_users(
    db: Session,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[UserDirectoryOut]:
    users = user_repository.list_users(db, role=role, status=status, skip=skip, limit=limit)
    results: List[UserDirectoryOut] = []
    for user in users:
        profile = user.student_profile if user.role == UserRole.student else user.lecturer_profile
        department = profile.department if profile is not None else None
        identifier = None
        if profile is not None:
            identifier = getattr(profile, "student_index_no", None) or getattr(profile, "lecturer_code", None)
        results.append(
            UserDirectoryOut(
                id=user.id,
                email=None,  # not stored locally — see UserOut note
                role=user.role,
                status=user.status,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                display_name=getattr(profile, "display_name", None),
                full_name=getattr(profile, "full_name", None),
                identifier=identifier,
                department_id=department.id if department else None,
                department_name=department.name if department else None,
            )
        )
    return results
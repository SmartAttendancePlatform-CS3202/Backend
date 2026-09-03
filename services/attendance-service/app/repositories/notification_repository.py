from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from shared_core.models.courses import Notice, NoticeReadStatus, Enrollment, CourseOffering
from shared_core.models.identity import User
from shared_core.models.enums import UserRole


def _visible(notice: Notice, user: User, db: Session) -> bool:
    role = getattr(user.role, "value", user.role)
    if notice.target_user_ids and user.id in notice.target_user_ids:
        return True
    if notice.target_roles and UserRole(role) in notice.target_roles:
        return True
    if notice.target_user_ids or notice.target_roles:
        return False
    if notice.course_offering_id:
        if role == "student":
            return db.query(Enrollment).filter(Enrollment.course_offering_id == notice.course_offering_id, Enrollment.student_id == user.id, Enrollment.is_active.is_(True)).first() is not None
        if role == "lecturer":
            offering = db.get(CourseOffering, notice.course_offering_id)
            return bool(offering and offering.lecturer_id == user.id)
    return True


def _serialize(notice: Notice, user_id: UUID, db: Session):
    read = db.query(NoticeReadStatus).filter(NoticeReadStatus.notice_id == notice.id, NoticeReadStatus.user_id == user_id).first()
    offering = db.get(CourseOffering, notice.course_offering_id) if notice.course_offering_id else None
    creator = db.get(User, notice.created_by) if notice.created_by else None
    read_count = db.query(NoticeReadStatus).filter(NoticeReadStatus.notice_id == notice.id).count()
    return {
        "id": notice.id, "course_offering_id": notice.course_offering_id, "course_code": getattr(offering, "offering_code", None),
        "title": notice.title, "body": notice.body, "urgency": notice.urgency, "created_by": notice.created_by,
        "creator_name": getattr(creator, "display_name", None) or getattr(creator, "username", None),
        "created_at": notice.created_at, "expires_at": notice.expires_at,
        "target_roles": notice.target_roles, "target_user_ids": notice.target_user_ids,
        "read_count": read_count, "is_read": read is not None,
    }


def get_notices(db: Session, user_id: UUID) -> List[dict]:
    user = db.get(User, user_id)
    notices = db.query(Notice).order_by(Notice.created_at.desc()).limit(200).all()
    return [_serialize(n, user_id, db) for n in notices if user and _visible(n, user, db) and (not n.expires_at or n.expires_at >= __import__('datetime').datetime.now(__import__('datetime').timezone.utc))]

def get_all_notices(db: Session) -> List[dict]:
    notices = db.query(Notice).order_by(Notice.created_at.desc()).limit(200).all()
    return [_serialize(n, n.created_by, db) for n in notices]


def create_notice(db: Session, data: dict, creator_id: UUID) -> dict:
    obj = Notice(**data, created_by=creator_id)
    db.add(obj); db.commit(); db.refresh(obj)
    return _serialize(obj, creator_id, db)


def mark_read(db: Session, notice_id: UUID, user_id: UUID):
    notice = db.get(Notice, notice_id)
    if not notice: return None
    existing = db.query(NoticeReadStatus).filter(NoticeReadStatus.notice_id == notice_id, NoticeReadStatus.user_id == user_id).first()
    if not existing:
        db.add(NoticeReadStatus(notice_id=notice_id, user_id=user_id)); db.commit()
    return _serialize(notice, user_id, db)

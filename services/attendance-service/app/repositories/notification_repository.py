from uuid import UUID
from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from shared_core.models.courses import Notice, NoticeReadStatus, Enrollment, CourseOffering
from shared_core.models.identity import User
from shared_core.models.enums import UserRole


def _visible_fast(notice: Notice, user: User, role: str, enrolled_offerings: set) -> bool:
    if role == "admin" or notice.created_by == user.id:
        return True
    if notice.target_user_ids and user.id in notice.target_user_ids:
        return True
    if notice.target_roles and UserRole(role) in notice.target_roles:
        return True
    if notice.target_user_ids or notice.target_roles:
        return False
    if notice.course_offering_id:
        if role == "student":
            return notice.course_offering_id in enrolled_offerings
        if role == "lecturer":
            offering = notice.course_offering
            return bool(offering and offering.lecturer_id == user.id)
    return True


def _serialize_batch(notice: Notice, read_count: int, is_read: bool):
    offering = notice.course_offering
    creator = notice.creator
    return {
        "id": notice.id, "course_offering_id": notice.course_offering_id, "course_code": getattr(offering, "offering_code", None),
        "title": notice.title, "body": notice.body, "urgency": notice.urgency, "created_by": notice.created_by,
        "creator_name": getattr(creator, "display_name", None) or getattr(creator, "username", None),
        "created_at": notice.created_at, "expires_at": notice.expires_at,
        "target_roles": notice.target_roles, "target_user_ids": notice.target_user_ids,
        "read_count": read_count, "is_read": is_read,
    }


def _get_batch_data(db: Session, notices: List[Notice], user_id: UUID):
    if not notices:
        return {}, set()
    notice_ids = [n.id for n in notices]
    
    counts = db.query(NoticeReadStatus.notice_id, func.count(NoticeReadStatus.id)).filter(NoticeReadStatus.notice_id.in_(notice_ids)).group_by(NoticeReadStatus.notice_id).all()
    count_map = {nid: cnt for nid, cnt in counts}
    
    read_map = set()
    if user_id:
        user_reads = db.query(NoticeReadStatus.notice_id).filter(NoticeReadStatus.notice_id.in_(notice_ids), NoticeReadStatus.user_id == user_id).all()
        read_map = {r[0] for r in user_reads}
    
    return count_map, read_map


def get_notices(db: Session, user_id: UUID) -> List[dict]:
    user = db.get(User, user_id)
    if not user: return []
    role = getattr(user.role, "value", user.role)
    
    enrolled_offerings = set()
    if role == "student":
        enrollments = db.query(Enrollment.course_offering_id).filter(Enrollment.student_id == user_id, Enrollment.is_active.is_(True)).all()
        enrolled_offerings = {e[0] for e in enrollments}

    notices = db.query(Notice).options(joinedload(Notice.creator), joinedload(Notice.course_offering)).order_by(Notice.created_at.desc()).limit(200).all()
    count_map, read_map = _get_batch_data(db, notices, user_id)
    
    now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    return [_serialize_batch(n, count_map.get(n.id, 0), n.id in read_map) for n in notices if _visible_fast(n, user, role, enrolled_offerings) and (not n.expires_at or n.expires_at >= now)]


def get_all_notices(db: Session, user_id: UUID | None = None) -> List[dict]:
    notices = db.query(Notice).options(joinedload(Notice.creator), joinedload(Notice.course_offering)).order_by(Notice.created_at.desc()).limit(200).all()
    count_map, read_map = _get_batch_data(db, notices, user_id)
    return [_serialize_batch(n, count_map.get(n.id, 0), n.id in read_map) for n in notices]


def create_notice(db: Session, data: dict, creator_id: UUID) -> dict:
    obj = Notice(**data, created_by=creator_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    obj = db.query(Notice).options(joinedload(Notice.creator), joinedload(Notice.course_offering)).filter(Notice.id == obj.id).first()
    return _serialize_batch(obj, 0, False)


def mark_read(db: Session, notice_id: UUID, user_id: UUID):
    notice = db.query(Notice).options(joinedload(Notice.creator), joinedload(Notice.course_offering)).filter(Notice.id == notice_id).first()
    if not notice: return None
    existing = db.query(NoticeReadStatus).filter(NoticeReadStatus.notice_id == notice_id, NoticeReadStatus.user_id == user_id).first()
    if not existing:
        db.add(NoticeReadStatus(notice_id=notice_id, user_id=user_id))
        db.commit()
    count = db.query(NoticeReadStatus).filter(NoticeReadStatus.notice_id == notice_id).count()
    return _serialize_batch(notice, count, True)

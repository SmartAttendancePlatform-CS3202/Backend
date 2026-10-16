from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from shared_core.models.courses import CourseOffering
from app.repositories import offering_repository


def _parse_time_str(val: str | None) -> int | None:
    if not val or not isinstance(val, str):
        return None
    raw = val.strip()
    parts = raw.split(":")
    if len(parts) >= 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            pass
    return None


def check_offering_overlap(
    db: Session,
    lecturer_id: UUID | None,
    day: str | None,
    start_time: str | None,
    end_time: str | None,
    venue_id: UUID | None = None,
    academic_year_id: UUID | None = None,
    semester: str | None = None,
    exclude_offering_id: UUID | None = None,
):
    if not lecturer_id or not day or not start_time or not end_time:
        return

    new_start = _parse_time_str(start_time)
    new_end = _parse_time_str(end_time)
    if new_start is None or new_end is None:
        return
    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be earlier than end time",
        )

    day_clean = day.strip().lower()

    # 1. Check Lecturer Overlap
    q_lecturer = db.query(CourseOffering).filter(
        CourseOffering.is_active.is_(True),
        CourseOffering.lecturer_id == lecturer_id,
    )
    if exclude_offering_id:
        q_lecturer = q_lecturer.filter(CourseOffering.id != exclude_offering_id)

    for off in q_lecturer.all():
        if academic_year_id and off.academic_year_id and off.academic_year_id != academic_year_id:
            continue
        if semester and off.semester and off.semester.strip().lower() != semester.strip().lower():
            continue
        if not off.day or off.day.strip().lower() != day_clean:
            continue
        off_start = _parse_time_str(off.start_time)
        off_end = _parse_time_str(off.end_time)
        if off_start is None or off_end is None:
            continue
        if max(new_start, off_start) < min(new_end, off_end):
            course_name = off.course.name if off.course else "another course"
            course_code = off.course.course_code if off.course else ""
            label = f"{course_code} - {course_name}" if course_code else course_name
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot overlap lectures at the same time: Lecturer already has a lecture scheduled for {label} on {off.day} from {off.start_time} to {off.end_time}.",
            )

    # 2. Check Venue Overlap
    if venue_id:
        q_venue = db.query(CourseOffering).filter(
            CourseOffering.is_active.is_(True),
            CourseOffering.venue_id == venue_id,
        )
        if exclude_offering_id:
            q_venue = q_venue.filter(CourseOffering.id != exclude_offering_id)

        for off in q_venue.all():
            if academic_year_id and off.academic_year_id and off.academic_year_id != academic_year_id:
                continue
            if semester and off.semester and off.semester.strip().lower() != semester.strip().lower():
                continue
            if not off.day or off.day.strip().lower() != day_clean:
                continue
            off_start = _parse_time_str(off.start_time)
            off_end = _parse_time_str(off.end_time)
            if off_start is None or off_end is None:
                continue
            if max(new_start, off_start) < min(new_end, off_end):
                venue_name = off.venue.name if off.venue else "Selected venue"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot overlap lectures at the same time: {venue_name} is already booked on {off.day} from {off.start_time} to {off.end_time}.",
                )


def get_all_offerings(db: Session, skip: int = 0, limit: int = 100):
    return offering_repository.get_all_offerings(db, skip=skip, limit=limit)


def get_offering(db: Session, offering_id: UUID):
    return offering_repository.get_offering(db, offering_id)


def get_offerings_by_course(db: Session, course_id: UUID, skip: int = 0, limit: int = 100):
    return offering_repository.get_offerings_by_course(db, course_id, skip=skip, limit=limit)


def create_offering(db: Session, data: dict, user_id: UUID):
    check_offering_overlap(
        db=db,
        lecturer_id=data.get("lecturer_id"),
        day=data.get("day"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        venue_id=data.get("venue_id"),
        academic_year_id=data.get("academic_year_id"),
        semester=data.get("semester"),
    )
    return offering_repository.create_offering(db, data, user_id)


def update_offering(db: Session, offering_id: UUID, update_data: dict):
    offering = offering_repository.get_offering(db, offering_id)
    if not offering:
        return None
    lecturer_id = update_data.get("lecturer_id", offering.lecturer_id)
    day = update_data.get("day", offering.day)
    start_time = update_data.get("start_time", offering.start_time)
    end_time = update_data.get("end_time", offering.end_time)
    venue_id = update_data.get("venue_id", offering.venue_id)
    academic_year_id = update_data.get("academic_year_id", offering.academic_year_id)
    semester = update_data.get("semester", offering.semester)

    check_offering_overlap(
        db=db,
        lecturer_id=lecturer_id,
        day=day,
        start_time=start_time,
        end_time=end_time,
        venue_id=venue_id,
        academic_year_id=academic_year_id,
        semester=semester,
        exclude_offering_id=offering_id,
    )
    return offering_repository.update_offering(db, offering, update_data)

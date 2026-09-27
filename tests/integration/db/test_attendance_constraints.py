import pytest
from sqlalchemy.exc import IntegrityError
import uuid
from shared_core.models.attendance import AttendanceRecord
from shared_core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

def test_enforce_attendance_foreign_key_constraints():
    """
    Test Case Name: Enforce_Attendance_Foreign_Key_Constraints
    Description: Directly executes SQL or ORM queries to attempt inserting an attendance record into the database with a non-existent user_id or session_id. It expects the database engine to reject the operation, ensuring orphan records cannot be created.
    """
    invalid_session_id = uuid.uuid4()
    invalid_student_id = uuid.uuid4()

    engine = create_engine(get_settings().database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    record = AttendanceRecord(
        lecture_session_id=invalid_session_id,
        student_id=invalid_student_id,
        status="present",
        first_check_in_at=datetime.now(timezone.utc)
    )

    db_session.add(record)
    
    with pytest.raises(IntegrityError) as excinfo:
        db_session.commit()
    
    # Assert that the error is due to a foreign key violation
    assert "ForeignKeyViolation" in str(excinfo.value) or "foreign key constraint" in str(excinfo.value).lower()
    
    db_session.rollback()
    db_session.close()

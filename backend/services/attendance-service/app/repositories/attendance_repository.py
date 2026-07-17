"""
Data-access layer for lecture_sessions, verification_windows,
attendance_records, and attendance_verification_attempts. Replace
stub bodies with real SQLAlchemy queries against
university_attendance_schema.sql.
"""


def create_session(offering):
    raise NotImplementedError


def schedule_check_in_window(session):
    raise NotImplementedError


def schedule_random_window(session, window_minutes: int):
    """Picks a random offset within the lecture duration server-side.
    Do not expose the chosen time to clients until the window opens."""
    raise NotImplementedError


def close_session(session_id):
    raise NotImplementedError


def get_open_window(lecture_session_id, window_type: str):
    raise NotImplementedError


def log_attempt(**kwargs):
    raise NotImplementedError


def upsert_first_check_in(lecture_session_id, student_id, attempt):
    raise NotImplementedError


def update_random_check_status(verification_window_id, student_id, attempt):
    raise NotImplementedError


def get_offering_report(course_offering_id):
    raise NotImplementedError

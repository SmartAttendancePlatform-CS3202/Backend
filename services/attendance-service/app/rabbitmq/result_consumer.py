from __future__ import annotations

import asyncio, json, logging, os
from datetime import datetime, timezone, timedelta
from uuid import UUID
import aio_pika
from sqlalchemy.orm import Session
from shared_core.db.session import get_session_factory
from shared_core.models.attendance import AttendanceRecord, AttendanceVerificationAttempt, VerificationWindow
from shared_core.models.enums import AttemptStatus, AttendanceStatus
from shared_core.schemas.events import FaceVerificationResult

logger = logging.getLogger(__name__)
_connection = None
_task = None


def _finalize_result(db: Session, result: FaceVerificationResult) -> None:
    existing = db.query(AttendanceVerificationAttempt).filter(AttendanceVerificationAttempt.id == result.attempt_id).first()
    if existing:
        return  # idempotent duplicate result
    window = db.query(VerificationWindow).filter(VerificationWindow.id == result.verification_window_id).first()
    if not window:
        logger.error("verification window %s not found", result.verification_window_id)
        return

    attempt = AttendanceVerificationAttempt(
        id=result.attempt_id,
        verification_window_id=result.verification_window_id,
        student_id=result.student_id,
        attempt_number=1,
        used_face_verification=True,
        used_location_check=True,
        face_match_confidence=result.confidence,
        status=AttemptStatus.success if result.face_match else AttemptStatus.failed,
        failure_reason=result.failure_reason or (None if result.face_match else "Face mismatch"),
        attempted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.lecture_session_id == window.lecture_session_id,
        AttendanceRecord.student_id == result.student_id,
    ).first()
    
    if not record:
        record = AttendanceRecord(
            id=__import__('uuid').uuid4(),
            lecture_session_id=window.lecture_session_id,
            student_id=result.student_id,
        )
        db.add(record)
        
    if getattr(window.window_type, "value", window.window_type) == "check_in":
        if result.face_match:
            now = datetime.now(timezone.utc)
            record.first_check_in_at = now
            session = window.lecture_session
            late_threshold = int(session.course_offering.late_threshold_minutes or 10)
            status = AttendanceStatus.late if now > session.scheduled_at + timedelta(minutes=late_threshold) else AttendanceStatus.present
            record.status = status
        else:
            record.status = AttendanceStatus.absent
            record.flag_reason = "Initial face verification failed"
    else:
        # If somehow it was a random check queue
        if result.face_match:
            record.random_check_completed_at = datetime.now(timezone.utc)
        else:
            record.status = AttendanceStatus.flagged_proxy
            record.flag_reason = "Random face verification failed"
            
    db.commit()
    db.commit()


async def _consume(message: aio_pika.IncomingMessage):
    try:
        result = FaceVerificationResult.model_validate_json(message.body)
        db = get_session_factory()()
        try:
            _finalize_result(db, result)
        finally:
            db.close()
        await message.ack()
    except Exception:
        logger.exception("Failed to consume AI result")
        await message.nack(requeue=False)


async def start_result_consumer():
    global _connection, _task
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    _connection = await aio_pika.connect_robust(url)
    channel = await _connection.channel()
    await channel.set_qos(prefetch_count=20)
    queue = await channel.declare_queue("face_verification_results", durable=True)
    await queue.consume(_consume)
    _task = asyncio.current_task()


async def stop_result_consumer():
    global _connection
    if _connection:
        await _connection.close()
        _connection = None

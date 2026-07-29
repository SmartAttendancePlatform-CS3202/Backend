import os
import aio_pika
import json
import asyncio
import base64
from uuid import UUID
import logging
from sqlalchemy.orm import Session
from shared_core.db.session import get_session_factory
from shared_core.schemas.events import FaceVerificationTask
from app.services import matching_service
from shared_core.models.attendance import AttendanceVerificationAttempt
from shared_core.models.enums import AttemptStatus

logger = logging.getLogger(__name__)

_connection = None
_channel = None

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = message.body.decode()
            data = json.loads(body)
            task = FaceVerificationTask(**data)
            
            # Process face verification
            # Since this is an async context, we should run synchronous DB/ML operations in a threadpool,
            # but for simplicity, we'll just run it directly. Fastapi/SQLAlchemy handles some synchronous calls well enough for a PoC.
            db = get_session_factory()()
            try:
                result = matching_service.verify_face(db, task.student_id, task.face_image_base64)
                
                # Create and commit the AttendanceVerificationAttempt directly
                attempt = AttendanceVerificationAttempt(
                    verification_window_id=task.verification_window_id,
                    student_id=UUID(task.student_id),
                    used_face_verification=True,
                    used_location_check=True,
                    latitude=task.latitude,
                    longitude=task.longitude,
                    face_match_confidence=result["confidence"],
                    status=AttemptStatus.success if result["is_match"] else AttemptStatus.failed,
                    failure_reason="Face mismatch" if not result["is_match"] else None
                )
                db.add(attempt)
                db.commit()
                
                # Also we should update the AttendanceRecord to set random_check_completed_at if success
                if result["is_match"]:
                    from shared_core.models.attendance import AttendanceRecord, VerificationWindow
                    from datetime import datetime
                    
                    window = db.query(VerificationWindow).filter(VerificationWindow.id == task.verification_window_id).first()
                    if window:
                        record = db.query(AttendanceRecord).filter(
                            AttendanceRecord.lecture_session_id == window.lecture_session_id,
                            AttendanceRecord.student_id == UUID(task.student_id)
                        ).first()
                        if record:
                            record.random_check_completed_at = datetime.utcnow()
                            db.commit()
                            
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def init_rabbitmq_consumer():
    global _connection, _channel
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    
    max_retries = 10
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            _connection = await aio_pika.connect_robust(rabbitmq_url)
            break
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(retry_delay)
            
    _channel = await _connection.channel()
    
    queue_name = os.environ.get("VERIFICATION_QUEUE_NAME", "face_verification_queue")
    queue = await _channel.declare_queue(queue_name, durable=True)
    
    await queue.consume(process_message)
    logger.info("RabbitMQ Consumer started and listening on queue: " + queue_name)

async def close_rabbitmq_consumer():
    if _connection:
        await _connection.close()

import os
import aio_pika
import json
import asyncio
import logging
from datetime import datetime
from uuid import UUID
from shared_core.db.session import get_session_factory
from shared_core.schemas.events import FaceVerificationResult
from shared_core.models.attendance import AttendanceVerificationAttempt, AttendanceRecord, VerificationWindow
from shared_core.models.enums import AttemptStatus

logger = logging.getLogger(__name__)

_connection = None
_channel = None

def _sync_process_verification_result(result: FaceVerificationResult):
    """
    Synchronous DB logic extracted to prevent blocking the async event loop.
    """
    db = get_session_factory()()
    try:
        status = AttemptStatus.success if result.is_match else AttemptStatus.failed
        failure_reason = None if result.is_match else "Face mismatch"
        
        attempt = AttendanceVerificationAttempt(
            verification_window_id=result.verification_window_id,
            student_id=UUID(result.student_id),
            used_face_verification=True,
            used_location_check=True,
            latitude=result.latitude,
            longitude=result.longitude,
            face_match_confidence=result.confidence,
            status=status,
            failure_reason=failure_reason
        )
        db.add(attempt)
        
        if result.is_match:
            window = db.query(VerificationWindow).filter(VerificationWindow.id == result.verification_window_id).first()
            if window:
                record = db.query(AttendanceRecord).filter(
                    AttendanceRecord.lecture_session_id == window.lecture_session_id,
                    AttendanceRecord.student_id == UUID(result.student_id)
                ).first()
                if record:
                    record.random_check_completed_at = datetime.utcnow()
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e  # Re-raise so the caller can catch it and route to DLQ
    finally:
        db.close()

async def process_verification_result(message: aio_pika.IncomingMessage):
    try:
        body = message.body.decode()
        data = json.loads(body)
        result = FaceVerificationResult(**data)
        
        # Offload synchronous blocking DB logic to a background thread
        await asyncio.to_thread(_sync_process_verification_result, result)
        
        # Acknowledge the message upon successful processing
        await message.ack()
                
    except Exception as e:
        logger.error(f"Error parsing/processing message, routing to DLQ: {e}")
        # Reject with requeue=False to route the poison pill message to the Dead Letter Exchange
        await message.reject(requeue=False)

async def init_result_consumer():
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
    
    queue_name = "verification_results_queue"
    
    # 1. Declare the Dead Letter Exchange (DLX)
    dlx_name = f"{queue_name}_dlx"
    dlx = await _channel.declare_exchange(dlx_name, aio_pika.ExchangeType.DIRECT, durable=True)
    
    # 2. Declare the Dead Letter Queue (DLQ) and bind it to the DLX
    dlq_name = f"{queue_name}_dlq"
    dlq = await _channel.declare_queue(dlq_name, durable=True)
    await dlq.bind(dlx)
    
    # 3. Declare the main queue with x-dead-letter-exchange configured
    queue = await _channel.declare_queue(
        queue_name, 
        durable=True,
        arguments={
            "x-dead-letter-exchange": dlx_name
        }
    )
    
    await queue.consume(process_verification_result)
    logger.info(f"RabbitMQ Result Consumer started and listening on queue: {queue_name}")

async def close_result_consumer():
    if _connection:
        await _connection.close()

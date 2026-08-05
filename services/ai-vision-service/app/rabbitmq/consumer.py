import os
import aio_pika
import json
import asyncio
import logging
from shared_core.db.session import get_session_factory
from shared_core.schemas.events import FaceVerificationTask, FaceVerificationResult
from app.services import matching_service

logger = logging.getLogger(__name__)

_connection = None
_channel = None
_publish_channel = None

def _sync_verify_face(student_id: str, face_image_base64: str) -> dict:
    """
    Synchronous DB logic extracted to prevent blocking the async event loop.
    """
    db = get_session_factory()()
    try:
        return matching_service.verify_face(db, student_id, face_image_base64)
    finally:
        db.close()

async def process_message(message: aio_pika.IncomingMessage):
    # Removing `async with message.process()` to handle ack/reject manually for DLQ routing
    try:
        body = message.body.decode()
        data = json.loads(body)
        task = FaceVerificationTask(**data)
        
        # Offload synchronous blocking DB and ML work to a background thread
        result = await asyncio.to_thread(_sync_verify_face, task.student_id, task.face_image_base64)
        
        verification_result = FaceVerificationResult(
            student_id=task.student_id,
            verification_window_id=task.verification_window_id,
            latitude=task.latitude,
            longitude=task.longitude,
            is_match=result["is_match"],
            confidence=result["confidence"]
        )
        
        if _publish_channel:
            exchange = _publish_channel.default_exchange
            await exchange.publish(
                aio_pika.Message(
                    body=verification_result.model_dump_json().encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="verification_results_queue"
            )
            
        # Acknowledge the message upon successful processing
        await message.ack()
            
    except Exception as e:
        logger.error(f"Error processing message, routing to DLQ: {e}")
        # Reject with requeue=False to route the poison pill message to the Dead Letter Exchange
        await message.reject(requeue=False)

async def init_rabbitmq_consumer():
    global _connection, _channel, _publish_channel
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
    _publish_channel = await _connection.channel()
    
    await _publish_channel.declare_queue("verification_results_queue", durable=True)
    
    queue_name = os.environ.get("VERIFICATION_QUEUE_NAME", "face_verification_queue")
    
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
    
    await queue.consume(process_message)
    logger.info(f"RabbitMQ Consumer started and listening on queue: {queue_name}")

async def close_rabbitmq_consumer():
    if _connection:
        await _connection.close()

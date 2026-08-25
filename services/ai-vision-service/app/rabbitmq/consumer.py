from __future__ import annotations
import asyncio, logging, os, time
import aio_pika
from aio_pika import ExchangeType
from shared_core.schemas.events import FaceVerificationTask, FaceVerificationResult
from app.services import matching_service
from shared_core.db.session import get_session_factory

logger = logging.getLogger(__name__)
_connection = None

async def _handle(message: aio_pika.IncomingMessage):
    try:
        retry_count = int((message.headers or {}).get("x-retry-count", 0))
        task = FaceVerificationTask.model_validate_json(message.body)
        started = time.perf_counter()
        db = get_session_factory()()
        try:
            result = await asyncio.to_thread(matching_service.verify_face, db, str(task.student_id), task.face_image_base64)
        finally:
            db.close()
        payload = FaceVerificationResult(
            event_id=task.event_id,
            attempt_id=task.attempt_id,
            student_id=task.student_id,
            verification_window_id=task.verification_window_id,
            face_match=result["is_match"],
            confidence=result["confidence"],
            processing_ms=int((time.perf_counter()-started)*1000),
        )
        channel = message.channel
        exchange = await channel.declare_exchange("face_verification_results_exchange", ExchangeType.DIRECT, durable=True)
        queue = await channel.declare_queue("face_verification_results", durable=True)
        await queue.bind(exchange, routing_key="face_verification_results")
        await exchange.publish(aio_pika.Message(body=payload.model_dump_json().encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="face_verification_results")
        await message.ack()
    except ValueError as exc:
        logger.warning("invalid face task: %s", exc)
        await message.nack(requeue=False)
    except Exception:
        logger.exception("AI verification failed")
        retry_count = int((message.headers or {}).get("x-retry-count", 0))
        if retry_count >= 2:
            dlx = await message.channel.declare_exchange("face_verification_dlx", ExchangeType.DIRECT, durable=True)
            dlq = await message.channel.declare_queue("face_verification_dead_letters", durable=True)
            await dlq.bind(dlx, routing_key="dead")
            headers = dict(message.headers or {})
            headers["x-retry-count"] = retry_count + 1
            await dlx.publish(aio_pika.Message(body=message.body, headers=headers, delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="dead")
            await message.ack()
        else:
            headers = dict(message.headers or {})
            headers["x-retry-count"] = retry_count + 1
            exchange = await message.channel.declare_exchange("face_verification_exchange", ExchangeType.DIRECT, durable=True)
            await exchange.publish(aio_pika.Message(body=message.body, headers=headers, delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="face_verification_queue")
            await message.ack()

async def init_rabbitmq_consumer():
    global _connection
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    for attempt in range(10):
        try:
            _connection = await aio_pika.connect_robust(url)
            channel = await _connection.channel()
            await channel.set_qos(prefetch_count=int(os.environ.get("AI_PREFETCH", "2")))
            exchange = await channel.declare_exchange("face_verification_exchange", ExchangeType.DIRECT, durable=True)
            queue = await channel.declare_queue("face_verification_queue", durable=True)
            await queue.bind(exchange, routing_key="face_verification_queue")
            await queue.consume(_handle)
            logger.info("AI Vision RabbitMQ consumer started")
            return
        except Exception as exc:
            if attempt == 9: raise
            logger.warning("RabbitMQ connection attempt %s failed: %s", attempt+1, exc)
            await asyncio.sleep(min(2**attempt, 10))

async def close_rabbitmq_consumer():
    global _connection
    if _connection:
        await _connection.close(); _connection=None

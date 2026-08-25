from __future__ import annotations

import asyncio, json, logging, os
import aio_pika
from aio_pika import ExchangeType
from shared_core.schemas.events import FaceVerificationTask

logger = logging.getLogger(__name__)
_connection = None
_channel = None
TASK_EXCHANGE = "face_verification_exchange"
TASK_QUEUE = "face_verification_queue"
RESULT_QUEUE = "face_verification_results"


async def init_rabbitmq() -> None:
    global _connection, _channel
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    for attempt in range(10):
        try:
            _connection = await aio_pika.connect_robust(url)
            _channel = await _connection.channel()
            await _channel.set_qos(prefetch_count=10)
            exchange = await _channel.declare_exchange(TASK_EXCHANGE, ExchangeType.DIRECT, durable=True)
            queue = await _channel.declare_queue(TASK_QUEUE, durable=True)
            await queue.bind(exchange, routing_key=TASK_QUEUE)
            await _channel.declare_queue(RESULT_QUEUE, durable=True)
            logger.info("RabbitMQ publisher ready")
            return
        except Exception:
            if attempt == 9:
                raise
            await asyncio.sleep(min(2 ** attempt, 10))


async def publish_verification_task(task: FaceVerificationTask) -> None:
    if _channel is None:
        raise RuntimeError("RabbitMQ publisher is not ready")
    exchange = await _channel.get_exchange(TASK_EXCHANGE)
    await exchange.publish(
        aio_pika.Message(
            body=task.model_dump_json().encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=str(task.event_id),
        ),
        routing_key=TASK_QUEUE,
    )


async def close_rabbitmq() -> None:
    global _connection
    if _connection:
        await _connection.close()
        _connection = None

import os
import aio_pika
import json
import asyncio
import logging
from shared_core.schemas.events import FaceVerificationTask

logger = logging.getLogger(__name__)

_connection = None
_channel = None

async def init_rabbitmq():
    global _connection, _channel
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    
    max_retries = 30
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
    logger.info("RabbitMQ Publisher started.")

async def close_rabbitmq():
    if _connection:
        await _connection.close()

async def publish_verification_task(task: FaceVerificationTask):
    if not _channel:
        logger.error("RabbitMQ channel is not initialized!")
        return

    queue_name = os.environ.get("VERIFICATION_QUEUE_NAME", "face_verification_queue")
    
    # Ensure the queue exists
    queue = await _channel.declare_queue(queue_name, durable=True)
    
    # Publish the message
    await _channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(task.model_dump(mode="json")).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        ),
        routing_key=queue_name
    )

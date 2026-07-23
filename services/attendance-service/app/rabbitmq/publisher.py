import os
import aio_pika
import json
from shared_core.schemas.events import FaceVerificationTask

# Global variable to hold the connection pool or channel pool
_connection_pool = None

async def get_connection() -> aio_pika.abc.AbstractRobustConnection:
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    return await aio_pika.connect_robust(rabbitmq_url)

async def init_rabbitmq():
    # Will be called on application startup
    pass

async def close_rabbitmq():
    # Will be called on application shutdown
    pass

async def publish_verification_task(task: FaceVerificationTask):
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue_name = os.environ.get("VERIFICATION_QUEUE_NAME", "face_verification_queue")
        
        # Ensure the queue exists
        queue = await channel.declare_queue(queue_name, durable=True)
        
        # Publish the message
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(task.model_dump(mode="json")).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue_name
        )

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.routers import verify
from app.rabbitmq.consumer import init_rabbitmq_consumer, close_rabbitmq_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_rabbitmq_consumer()
    yield
    # Shutdown
    await close_rabbitmq_consumer()

app = FastAPI(title="AI Vision Service", lifespan=lifespan)

app.include_router(verify.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-vision-service"}

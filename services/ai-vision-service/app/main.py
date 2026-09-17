from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from prometheus_fastapi_instrumentator import Instrumentator
from shared_core.openapi import API_INDEX_HTML, SWAGGER_UI_PARAMETERS, service_description
from shared_core.logging import setup_logging
from shared_core.middleware import RequestGuardMiddleware, StructlogMiddleware
from app.routers import verify
from app.rabbitmq.consumer import init_rabbitmq_consumer, close_rabbitmq_consumer
from shared_core.telemetry import setup_telemetry, instrument_app
setup_telemetry("ai-service") 
setup_logging("ai-vision-service")
@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_rabbitmq_consumer(); yield; await close_rabbitmq_consumer()
app=FastAPI(title="AI Vision Service",version="2.0.0",description=service_description("Internal face embedding and verification service. No client-facing endpoints."),swagger_ui_parameters=SWAGGER_UI_PARAMETERS,lifespan=lifespan)
app.add_middleware(RequestGuardMiddleware); app.add_middleware(StructlogMiddleware)
# CORS intentionally disabled for client use; internal calls use service authentication.
Instrumentator().instrument(app).expose(app)
instrument_app(app)
app.include_router(verify.router)
@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def root(): return API_INDEX_HTML
@app.get("/health")
def health(): return {"status":"ok","service":"ai-vision-service"}

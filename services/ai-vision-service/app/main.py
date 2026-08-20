from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from prometheus_fastapi_instrumentator import Instrumentator

from shared_core.openapi import API_INDEX_HTML, SWAGGER_UI_PARAMETERS, service_description

from app.routers import verify
from app.rabbitmq.consumer import init_rabbitmq_consumer, close_rabbitmq_consumer
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your web dashboard's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
OPENAPI_TAGS = [
    {
        "name": "verification",
        "description": "Face embedding register & match (internal callers only — X-Internal-Key)",
    },
    {"name": "health", "description": "Service health"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_rabbitmq_consumer()
    yield
    await close_rabbitmq_consumer()


app = FastAPI(
    title="AI Vision Service",
    version="1.0.0",
    description=service_description(
        """
Internal face embedding + matching API. Intended for service-to-service calls
from attendance-service (not end-user browsers in production).

**Local base URL:** `http://localhost:8003`  
**Swagger:** `/docs` · **ReDoc:** `/redoc` · **OpenAPI JSON:** `/openapi.json`

Authorize with **InternalApiKey** = value of `INTERNAL_API_KEY` in `.env`.
"""
    ),
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    lifespan=lifespan,
    contact={
        "name": "Smart Attendance Platform",
        "url": "https://github.com/SmartAttendancePlatform-CS3202/Backend",
    },
)

Instrumentator().instrument(app).expose(app)

app.include_router(verify.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def api_index():
    return API_INDEX_HTML


@app.get("/health", tags=["health"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "ai-vision-service"}

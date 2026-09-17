"""AI Vision HTTP client with Prometheus latency metrics.

Face registration (onboarding) uses HTTP. Attendance verification uses RabbitMQ
asynchronously; ``verify_face`` remains for diagnostics/tests only.
"""
import os
import time
import httpx
from shared_core.config import get_settings
from prometheus_client import Histogram

AI_VISION_LATENCY_SECONDS = Histogram(
    "ai_vision_latency_seconds",
    "Total time for ai-vision-service requests in seconds",
    ["endpoint", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)


def _base_url() -> str:
    return os.environ.get("AI_VISION_SERVICE_URL", "http://ai-vision-service:8000")


def _headers() -> dict[str, str]:
    return {"X-Internal-Key": get_settings().internal_api_key}


async def register_face(student_id: str, face_image_base64: str) -> dict:
    start = time.perf_counter()
    status_code = "500"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{_base_url()}/internal/register",
                json={"student_id": student_id, "face_image_base64": face_image_base64},
                headers=_headers(),
            )
            status_code = str(response.status_code)
            response.raise_for_status()
            return response.json()
    finally:
        AI_VISION_LATENCY_SECONDS.labels(
            endpoint="register",
            status_code=status_code,
        ).observe(time.perf_counter() - start)


def verify_face(student_id: str, face_image_base64: str) -> dict:
    start = time.perf_counter()
    status_code = "500"
    try:
        response = httpx.post(
            f"{_base_url()}/internal/verify",
            json={"student_id": student_id, "face_image_base64": face_image_base64},
            headers=_headers(),
            timeout=10.0,
        )
        status_code = str(response.status_code)
        response.raise_for_status()
        return response.json()
    finally:
        AI_VISION_LATENCY_SECONDS.labels(
            endpoint="verify",
            status_code=status_code,
        ).observe(time.perf_counter() - start)

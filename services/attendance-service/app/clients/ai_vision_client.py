"""Deprecated synchronous AI Vision client.

Attendance verification uses RabbitMQ asynchronously. This client remains only for
small internal diagnostics/tests and never receives user traffic.
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


def verify_face(student_id: str, face_image_base64: str) -> dict:
    base_url = os.environ.get("AI_VISION_SERVICE_URL", "http://ai-vision-service:8000")
    start = time.perf_counter()
    status_code = "500"
    try:
        response = httpx.post(
            f"{base_url}/internal/verify",
            json={"student_id": student_id, "face_image_base64": face_image_base64},
            headers={"X-Internal-Key": get_settings().internal_api_key},
            timeout=10.0,
        )
        status_code = str(response.status_code)
        response.raise_for_status()
        return response.json()
    finally:
        AI_VISION_LATENCY_SECONDS.labels(endpoint="verify", status_code=status_code).observe(time.perf_counter() - start)

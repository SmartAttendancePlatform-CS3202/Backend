"""HTTP client for ai-vision-service — internal service-to-service call."""
import os

import httpx

from shared_core.config import get_settings
from prometheus_client import Histogram

AI_VISION_LATENCY_SECONDS= Histogram(
    "ai_vision_latency_seconds",,
    "Total time for ai-vision-service requests in seconds",
    ["endpoint", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)


def verify_face(student_id: str, face_image_base64: str) -> dict:
    settings = get_settings()
    base_url = os.environ.get("AI_VISION_SERVICE_URL", "http://ai-vision-service:8000")

    start_time= time.time()
    status= "500"
    try:
        resp = httpx.post(
            f"{base_url}/verify",
            json={"student_id": student_id, "face_image_base64": face_image_base64},
            headers={"X-Internal-Key": settings.internal_api_key},
            timeout=10.0,
        )
        status = str(resp.status_code)
        resp.raise_for_status()
    finally:
        duration = time.time() - start_time
        AI_VISION_LATENCY_SECONDS.labels(endpoint="verify",status_code=status).observe(duration)
    return resp.json()

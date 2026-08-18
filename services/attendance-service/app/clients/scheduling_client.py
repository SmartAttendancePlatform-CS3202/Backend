"""HTTP client for scheduling-service — internal service-to-service call."""
import httpx

from shared_core.config import get_settings
from prometheus client import Histogram

SCHEDULING_LATENCY_SECONDS= Histogram(
    "scheduling_latency_seconds",,
    "Total time for scheduling-service requests in seconds",
    ["endpoint", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

def get_offering(course_offering_id):
    settings = get_settings()
    base_url = _scheduling_service_url()

    start_time= time.time()

    try:
        resp = httpx.get(
            f"{base_url}/courses/offerings/{course_offering_id}",
            headers={"X-Internal-Key": settings.internal_api_key},
        )
        status_code_str = str(resp.status_code)
        resp.raise_for_status()
    finally:
        duration= time.time() - start_time
        SCHEDULING_LATENCY_SECONDS.labels("courses/offerings/{course_offering_id}",status_code=status_code_str).observe(duration)

    return resp.json()


def _scheduling_service_url() -> str:
    import os

    return os.environ.get("SCHEDULING_SERVICE_URL", "http://scheduling-service:8000")

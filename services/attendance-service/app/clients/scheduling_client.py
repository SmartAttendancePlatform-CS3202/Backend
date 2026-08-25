import os
import time
import httpx
from prometheus_client import Histogram
from shared_core.config import get_settings

SCHEDULING_LATENCY_SECONDS = Histogram(
    "scheduling_latency_seconds",
    "Total time for scheduling-service requests in seconds",
    ["endpoint", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)


def _headers() -> dict[str, str]:
    return {"X-Internal-Key": get_settings().internal_api_key}


def _url() -> str:
    return os.environ.get("SCHEDULING_SERVICE_URL", "http://scheduling-service:8000")


def get_offering(course_offering_id):
    start_time = time.time()
    status = "500"
    try:
        resp = httpx.get(f"{_url()}/offerings/internal/{course_offering_id}", headers=_headers(), timeout=5.0)
        status = str(resp.status_code)
        resp.raise_for_status()
        return resp.json()
    finally:
        duration = time.time() - start_time
        SCHEDULING_LATENCY_SECONDS.labels(
            endpoint="offerings/internal/{course_offering_id}",
            status=status,
        ).observe(duration)

def get_venue(venue_id):
    resp = httpx.get(f"{_url()}/venues/internal/{venue_id}", headers=_headers(), timeout=5.0)
    resp.raise_for_status()
    return resp.json()

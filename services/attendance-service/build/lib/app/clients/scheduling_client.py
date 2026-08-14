"""HTTP client for scheduling-service — internal service-to-service call."""
import httpx

from shared_core.config import get_settings


def get_offering(course_offering_id):
    settings = get_settings()
    base_url = _scheduling_service_url()
    resp = httpx.get(
        f"{base_url}/courses/offerings/{course_offering_id}",
        headers={"X-Internal-Key": settings.internal_api_key},
    )
    resp.raise_for_status()
    return resp.json()


def _scheduling_service_url() -> str:
    import os

    return os.environ.get("SCHEDULING_SERVICE_URL", "http://scheduling-service:8000")

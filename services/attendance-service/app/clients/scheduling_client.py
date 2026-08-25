import os
import httpx
from shared_core.config import get_settings


def _headers() -> dict[str, str]:
    return {"X-Internal-Key": get_settings().internal_api_key}


def _url() -> str:
    return os.environ.get("SCHEDULING_SERVICE_URL", "http://scheduling-service:8000")


def get_offering(course_offering_id):
    resp = httpx.get(f"{_url()}/offerings/internal/{course_offering_id}", headers=_headers(), timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def get_venue(venue_id):
    resp = httpx.get(f"{_url()}/venues/internal/{venue_id}", headers=_headers(), timeout=5.0)
    resp.raise_for_status()
    return resp.json()

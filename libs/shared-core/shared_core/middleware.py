from __future__ import annotations

import structlog
import time
import uuid
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared_core.config import get_settings


class RequestGuardMiddleware(BaseHTTPMiddleware):
    """Request size + simple local rate limit + request id.

    Kong should provide the distributed rate limiter in production; this middleware is a safe
    per-instance fallback and enforces request-size limits at every service.
    """
    _requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        limit = get_settings().max_request_bytes
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > limit:
            return JSONResponse({"detail": "Request body too large", "request_id": request_id}, status_code=413)

        now = time.monotonic()
        key = request.client.host if request.client else "unknown"
        bucket = self._requests[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= get_settings().rate_limit_per_minute:
            return JSONResponse({"detail": "Rate limit exceeded", "request_id": request_id}, status_code=429)
        bucket.append(now)

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class StructlogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bind request-specific information to the logger context
        log = structlog.get_logger()
        
        # Capture method and path
        log = log.bind(
            method=request.method,
            path=request.url.path,
        )

        start_time = time.time()
        
        try:
            # Pass the request to the next middleware / endpoint
            response = await call_next(request)
            
            # Log the successful completion
            process_time = time.time() - start_time
            log.info(
                "request_completed", 
                status_code=response.status_code,
                process_time=f"{process_time:.4f}s"
            )
            return response
            
        except Exception as e:
            # Log any unhandled exceptions
            process_time = time.time() - start_time
            log.error(
                "request_failed", 
                error=str(e),
                process_time=f"{process_time:.4f}s"
            )
            raise e

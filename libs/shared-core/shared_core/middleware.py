import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger("api.middleware")

class StructlogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Bind to context so all subsequent logs in this request have it
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log successful requests
            process_time = time.time() - start_time
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_s=round(process_time, 4)
            )
            return response
            
        except Exception as e:
            # Log exceptions explicitly
            process_time = time.time() - start_time
            logger.exception(
                "request_failed",
                duration_s=round(process_time, 4)
            )
            raise e

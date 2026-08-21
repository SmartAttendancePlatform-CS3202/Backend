import logging
import sys
from typing import Any, Dict

import structlog

def setup_logging(service_name: str, log_level: int = logging.INFO):
    """
    Configure structlog and standard logging for a microservice.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.contextvars.bind_contextvars(service=service_name)
    
    # Configure uvicorn to use structlog
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = [logging.StreamHandler(sys.stdout)]
    
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = [logging.StreamHandler(sys.stdout)]

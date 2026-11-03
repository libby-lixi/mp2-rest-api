import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    """Log one request and attach its request ID to the response."""
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id

    # start the stopwatch
    started = time.perf_counter()

    try:
        # let the request go to its door (upload, health, etc)
        response = await call_next(request)
    except Exception:
        # TODO 1: Log the unexpected exception at ERROR with exc_info=True.
        # log it as an error with the full traceback (exc_info=True)
        logger.error(f"Unexpected error: request_id={request_id}", exc_info=True)
    
        # give the user a plain message without showing them the private error details
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # stop the stopwatch and turn the seconds into milliseconds
    duration_ms = (time.perf_counter() - started) * 1000

    # TODO 2: Build a message containing request_id, request.method,
    # request.url.path, response.status_code, and duration_ms.
    message = (
        f"request_id={request_id} {request.method} {request.url.path} "
        f"status={response.status_code} duration={duration_ms:.1f}ms"
    )

    # TODO 3: Log that message at ERROR for 5xx, WARNING for 4xx,
    # and INFO for other responses.
    if response.status_code >= 500:
        logger.error(message)
    elif response.status_code >= 400:
        logger.warning(message)
    else:
        logger.info(message)

    response.headers["X-Request-ID"] = request_id
    return response
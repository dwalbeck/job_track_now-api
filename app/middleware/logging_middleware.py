import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""

    async def dispatch(self, request: Request, call_next):
        # Record start time
        start_time = time.time()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log the request
        logger.log_request(
            method=request.method,
            path=str(request.url.path),
            client_ip=client_ip
        )

        # Log query parameters if present
        if request.query_params:
            logger.debug(f"Query parameters: {dict(request.query_params)}")

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log the response
            logger.log_response(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            return response

        except Exception as e:
            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000

            # Log the error
            logger.log_error_with_context(
                error=e,
                context=f"{request.method} {request.url.path} ({duration_ms:.2f}ms)"
            )

            # Re-raise the exception
            raise
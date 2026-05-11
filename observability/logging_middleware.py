import json
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gateway.access")

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides structured JSON logging for all incoming requests.
    
    Each log entry includes a unique correlation ID (request_id) to allow 
    tracing a single request through the system. This is essential for 
    high-scale production observability.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercepts each request to record metrics and log structured data.
        
        Captures method, path, status code, duration, and client metadata.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as e:
            # Ensure we log the failure before raising
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_request(request, 500, duration_ms, request_id, error=str(e))
            raise e

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._log_request(request, response.status_code, duration_ms, request_id)

        response.headers["X-Request-ID"] = request_id
        return response

    def _log_request(self, request: Request, status_code: int, duration_ms: float, request_id: str, error: str = None):
        """Helper to format and output the structured log."""
        log_data = {
            "timestamp": time.time(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        if error:
            log_data["error"] = error
            logger.error(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))

import json
import time
from starlette.middleware.base import BaseHTTPMiddleware
from application.logger import logger

MAX_BODY_LOG_SIZE = 2048


def _parse_body(raw: bytes) -> str:
    if not raw:
        return "-"
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.dumps(json.loads(text), separators=(",", ":"))
    except (json.JSONDecodeError, ValueError):
        return text[:MAX_BODY_LOG_SIZE]


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        request_body = await request.body()
        payload = _parse_body(request_body)

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            "API request processed",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "response_time": process_time,
                "payload": payload,
            },
        )

        return response
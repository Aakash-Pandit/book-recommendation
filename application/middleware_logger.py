import json
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from application.async_logger import request_id_var
from application.logger import logger

MAX_BODY_LOG_SIZE = 2048
_SENSITIVE_KEYS = frozenset({
    "password", "token", "secret", "authorization",
    "api_key", "access_token", "refresh_token",
})


def _mask_sensitive(data: dict) -> dict:
    return {k: "***" if k.lower() in _SENSITIVE_KEYS else v for k, v in data.items()}


def _parse_body(raw: bytes) -> str:
    if not raw:
        return "-"
    text = raw.decode("utf-8", errors="replace")[:MAX_BODY_LOG_SIZE]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = _mask_sensitive(parsed)
        return json.dumps(parsed, separators=(",", ":"))
    except (json.JSONDecodeError, ValueError):
        return text


def _log_fn(status_code: int):
    if status_code >= 500:
        return logger.error
    if status_code >= 400:
        return logger.warning
    return logger.info


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)  # propagates to all loggers in this request

        request_body = await request.body()
        payload = _parse_body(request_body)

        path = request.url.path
        query = str(request.query_params)
        endpoint = f"{path}?{query}" if query else path

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        _log_fn(response.status_code)(
            "API request processed",
            extra={
                "endpoint": endpoint,
                "method": request.method,
                "status_code": response.status_code,
                "response_time": process_time,
                "payload": payload,
                "request_id": request_id,
            },
        )

        return response

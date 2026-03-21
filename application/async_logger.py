import atexit
import json
import logging
import os
import queue
import socket
import sys
import threading
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

SERVICE_NAME = os.getenv("SERVICE_NAME", "book-recommendation")
HOSTNAME = socket.gethostname()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
MAX_FILE_BYTES = int(os.getenv("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10 MB
MAX_BACKUP_COUNT = 5
QUEUE_MAX_SIZE = 10_000

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Set once per request in middleware; automatically available to any logger
# called during that request without passing it through every function call.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

log_queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAX_SIZE)
_SENTINEL = object()


@dataclass
class LogEntry:
    timestamp: str
    level: str
    method: str
    endpoint: str
    status_code: int
    response_time: float
    payload: str
    request_id: str
    message: str
    service: str
    host: str


class Worker(threading.Thread):

    def run(self):
        while True:
            batch = []

            entry = log_queue.get()

            if entry is _SENTINEL:
                break

            batch.append(entry)

            while True:
                try:
                    entry = log_queue.get_nowait()
                    if entry is _SENTINEL:
                        self._flush(batch)
                        return
                    batch.append(entry)
                    if len(batch) >= 50:
                        break
                except queue.Empty:
                    break

            self._flush(batch)

    def _flush(self, batch: list):
        stdout_lines = "".join(
            f"{e.timestamp} | {e.level:<8} | {e.method}: {e.endpoint} | "
            f"status={e.status_code} | {e.response_time:.3f}s | "
            f"req_id={e.request_id} | payload={e.payload} | {e.message}\n"
            for e in batch
        )
        sys.stdout.write(stdout_lines)
        sys.stdout.flush()

        self._rotate_if_needed()

        json_lines = [json.dumps(asdict(e)) + "\n" for e in batch]
        with open(LOG_FILE, "a") as f:
            f.writelines(json_lines)

    def _rotate_if_needed(self):
        if not os.path.exists(LOG_FILE):
            return
        if os.path.getsize(LOG_FILE) < MAX_FILE_BYTES:
            return
        for i in range(MAX_BACKUP_COUNT - 1, 0, -1):
            src = f"{LOG_FILE}.{i}"
            dst = f"{LOG_FILE}.{i + 1}"
            if os.path.exists(src):
                os.rename(src, dst)
        os.rename(LOG_FILE, f"{LOG_FILE}.1")


class AsyncHandler(logging.Handler):

    def emit(self, record):
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            level=record.levelname,
            method=getattr(record, "method", "-"),
            endpoint=getattr(record, "endpoint", "-"),
            status_code=getattr(record, "status_code", 0),
            response_time=getattr(record, "response_time", 0.0),
            payload=getattr(record, "payload", "-"),
            # Use explicitly passed request_id, fall back to context var so any
            # logger called mid-request gets the id without passing it manually.
            request_id=getattr(record, "request_id", None) or request_id_var.get(),
            message=record.getMessage(),
            service=SERVICE_NAME,
            host=HOSTNAME,
        )
        try:
            log_queue.put_nowait(entry)
        except queue.Full:
            pass  # drop rather than block the request thread


def _shutdown():
    log_queue.put(_SENTINEL)
    worker.join(timeout=5.0)


worker = Worker(daemon=True)
worker.start()
atexit.register(_shutdown)

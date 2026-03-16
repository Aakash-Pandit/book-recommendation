import logging
import queue
import sys
import threading
from datetime import datetime, timezone

log_queue = queue.Queue()


class Worker(threading.Thread):

    def run(self):
        while True:
            batch = []

            try:
                record = log_queue.get(timeout=1.0)
                batch.append(record)
            except queue.Empty:
                continue

            while True:
                try:
                    batch.append(log_queue.get_nowait())
                    if len(batch) >= 50:
                        break
                except queue.Empty:
                    break

            self._flush(batch)

    def _flush(self, batch):
        for timestamp, level, endpoint, method, status_code, response_time, message in batch:
            sys.stdout.write(
                f"{timestamp} | {level:<8} | {method} {endpoint} | "
                f"status={status_code} | {response_time:.3f}s | {message}\n"
            )
        sys.stdout.flush()


class AsyncHandler(logging.Handler):

    def emit(self, record):
        log_queue.put((
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            record.levelname,
            getattr(record, "endpoint", "-"),
            getattr(record, "method", "-"),
            getattr(record, "status_code", 0),
            getattr(record, "response_time", 0.0),
            record.getMessage(),
        ))


worker = Worker(daemon=True)
worker.start()

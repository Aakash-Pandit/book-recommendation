import logging
import os
import queue
import sys
import threading
from datetime import datetime, timezone

LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

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
        lines = [
            f"{timestamp} | {level:<8} | {method}: {endpoint} | "
            f"status={status_code} | {response_time:.3f}s | payload={payload} | {message}\n"
            for timestamp, level, endpoint, method, status_code, response_time, payload, message in batch
        ]
        for line in lines:
            sys.stdout.write(line)
        sys.stdout.flush()

        with open(LOG_FILE, "a") as f:
            f.writelines(lines)


class AsyncHandler(logging.Handler):

    def emit(self, record):
        log_queue.put((
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            record.levelname,
            getattr(record, "endpoint", "-"),
            getattr(record, "method", "-"),
            getattr(record, "status_code", 0),
            getattr(record, "response_time", 0.0),
            getattr(record, "payload", "-"),
            record.getMessage(),
        ))


worker = Worker(daemon=True)
worker.start()

import logging
import queue
import threading
from datetime import datetime

log_queue = queue.Queue()


class Worker(threading.Thread):

    def run(self):
        batch = []
        
        while True:
            record = log_queue.get()
            batch.append(record)
            
            if len(batch) >= 50:
                try:
                    #TODO: log here
                    pass
                except Exception as e:
                    print("Error while logging:", e)

                batch.clear()


class AsyncHandler(logging.Handler):

    def emit(self, record):
        log_entry = (
            datetime.utcnow(),
            record.levelname,
            record.pathname,
            getattr(record, "endpoint", ""),
            getattr(record, "method", ""),
            getattr(record, "status_code", 0),
            getattr(record, "response_time", 0),
            record.getMessage(),
        )

        log_queue.put(log_entry)


worker = Worker(daemon=True)
worker.start()
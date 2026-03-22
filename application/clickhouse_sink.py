import os
import sys
import threading
from datetime import datetime

import clickhouse_connect

_client = None
_client_lock = threading.Lock()


def _create_client():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.getenv("CLICKHOUSE_PORT", 8123)),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        database=os.getenv("CLICKHOUSE_DB", "default"),
        connect_timeout=5,
        send_receive_timeout=10,
    )


def get_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = _create_client()
    return _client


def _reset_client():
    global _client
    with _client_lock:
        _client = None


def insert_batch(batch: list) -> None:
    rows = [
        [
            datetime.strptime(e.timestamp, "%Y-%m-%d %H:%M:%S"),
            e.level, e.method, e.endpoint,
            e.status_code, e.response_time, e.payload,
            e.request_id, e.message, e.service, e.host,
        ]
        for e in batch
    ]
    try:
        get_client().insert(
            "app_logs",
            rows,
            column_names=[
                "timestamp", "level", "method", "endpoint",
                "status_code", "response_time", "payload",
                "request_id", "message", "service", "host",
            ],
        )
    except Exception as exc:
        _reset_client()  # force reconnect on next attempt
        sys.stderr.write(f"[clickhouse_sink] insert failed, will reconnect: {exc}\n")
        raise

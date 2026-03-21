import os
from datetime import datetime
import clickhouse_connect

_client = None


def get_client():
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            port=int(os.getenv("CLICKHOUSE_PORT", 8123)),
            username=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            database=os.getenv("CLICKHOUSE_DB", "default"),
        )
    return _client


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
    get_client().insert(
        "app_logs",
        rows,
        column_names=[
            "timestamp", "level", "method", "endpoint",
            "status_code", "response_time", "payload",
            "request_id", "message", "service", "host",
        ],
    )

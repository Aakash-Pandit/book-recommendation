CREATE DATABASE IF NOT EXISTS clickhouse;

CREATE TABLE IF NOT EXISTS clickhouse.app_logs (
    timestamp     DateTime,
    level         LowCardinality(String),
    method        LowCardinality(String),
    endpoint      String,
    status_code   UInt16,
    response_time Float32,
    payload       String,
    request_id    String,
    message       String,
    service       LowCardinality(String),
    host          LowCardinality(String)
)
ENGINE = MergeTree()
ORDER BY (timestamp, service, level)
TTL timestamp + INTERVAL 30 DAY;

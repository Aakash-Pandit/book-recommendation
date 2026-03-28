# Book Recommendation System

A FastAPI-based REST API that provides book recommendations using collaborative filtering and popularity-based ranking, with structured request logging to ClickHouse and observability dashboards via Grafana.

## Overview

This project uses a pre-trained similarity model (built in the [notebooks/](notebooks/) directory) to serve two types of book recommendations:

- **Popular books** — top books ranked by rating count and average rating
- **Collaborative filtering** — similar books based on a user-item pivot table and cosine similarity scores

Every API request is logged asynchronously to **ClickHouse** (columnar database) for queryable analytics. **Grafana** connects to ClickHouse to provide live dashboards — request rate, error rate, response times, and per-endpoint breakdowns.

## Project Structure

```
book-recommendation/
├── application/
│   ├── api.py                  # FastAPI routes
│   ├── recommendation.py       # Recommendation logic
│   ├── async_logger.py         # Async queue-based log handler
│   ├── logger.py               # Logger configuration
│   ├── middleware_logger.py    # Request/response logging middleware
│   └── clickhouse_sink.py      # ClickHouse batch insert sink
├── compose/
│   ├── Dockerfile              # FastAPI container image
│   └── clickhouse/
│       ├── init.sql            # Auto-creates DB and table on first start
│       └── override-networks.xml  # Allows external connections to ClickHouse
├── notebooks/
│   ├── main.ipynb              # Data processing & model training
│   ├── csv_data/               # Raw datasets (Books, Ratings, Users)
│   ├── books.pkl
│   ├── popular.pkl
│   ├── pivot_table.pkl
│   └── similarity_score.pkl
├── logs/                       # Auto-created, git-ignored
│   └── app.log
├── tests/
│   ├── test_api.py             # API test cases
│   └── test_logging.py         # Logging test cases
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline
├── .env                        # ClickHouse + service env vars (not committed)
├── run.py                      # App entrypoint (uvicorn)
├── pytest.ini
├── requirements.txt
├── docker-compose.yml
└── Makefile
```

## API Endpoints

### `GET /`
Health check.

```json
{"message": "Welcome to Book Recommendation API!"}
```

### `GET /api/popular_books`
Returns a list of popular books.

```json
{
  "popular_books": [
    {"title": "...", "author": "...", "image_url": "..."}
  ]
}
```

### `POST /api/recommend_books`
Returns books similar to a given title using collaborative filtering.

**Request body:**
```json
{
  "name_of_book": "The Da Vinci Code",
  "number_of_recommendations": 5
}
```

**Response:**
```json
{
  "recommendations": [
    {"title": "...", "author": "...", "image_url": "..."}
  ]
}
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- Ports `8000`, `8123`, `9000`, `3000` free on your machine

---

## Quick Start

### 1. Clone the repo

```bash
git clone <repo-url>
cd book-recommendation
```

### 2. Create the `.env` file

Create a `.env` file in the project root with the following content:

```env
# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DB=clickhouse
SERVICE_NAME=book-recommendation

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
GF_INSTALL_PLUGINS=grafana-clickhouse-datasource
```

> `.env` is git-ignored — never commit it with real credentials.

### 3. Start the full stack

```bash
docker compose up -d
```

This starts three services:

| Service | URL | Credentials |
|---|---|---|
| FastAPI | `http://localhost:8000` | — |
| ClickHouse | `http://localhost:8123/play` | user: `default`, password: _(empty)_ |
| Grafana | `http://localhost:3000` | `admin / admin` |

On first boot, `compose/clickhouse/init.sql` automatically creates the `clickhouse` database and `app_logs` table — no manual SQL needed.

### 4. Verify everything is running

```bash
docker compose ps
```

All three services should show `Up`.

```bash
# Test the API
curl http://localhost:8000/
curl http://localhost:8000/api/popular_books

# Verify logs are reaching ClickHouse
curl -X POST "http://localhost:8123" \
  --data "SELECT count() FROM clickhouse.app_logs"
```

### 5. Stop the stack

```bash
docker compose down        # stop containers, keep volumes
docker compose down -v     # stop containers AND delete all data
```

---

## Running Locally (without Docker)

```bash
pip install -r requirements.txt
python run.py
```

> ClickHouse and Grafana require Docker. Running without Docker only starts the FastAPI server; logs will be written to stdout and `logs/app.log` only.

---

## Testing

```bash
make test          # Run tests via Docker
pytest tests/ -v   # Run tests locally
```

## Logging

Every request is logged asynchronously via a queue-based worker (bounded queue, batch flush, graceful shutdown on SIGTERM) to avoid blocking request handlers.

Logs are written to three destinations simultaneously:

| Destination | Format | Purpose |
|---|---|---|
| stdout | Human-readable | Terminal / `docker compose logs` |
| `logs/app.log` | JSON lines, auto-rotated at 10 MB | Local persistence |
| ClickHouse `app_logs` table | Columnar rows | Queryable analytics |

Each stdout line follows this format:
```
2026-03-22 10:23:01 | INFO     | GET: /api/popular_books | status=200 | 0.012s | req_id=abc-123 | payload=- | API request processed
```

### Log fields

| Field | Description |
|---|---|
| `timestamp` | UTC time of the request |
| `level` | `INFO` (2xx), `WARNING` (4xx), `ERROR` (5xx) |
| `method` | HTTP method |
| `endpoint` | Path + query string |
| `status_code` | HTTP response status |
| `response_time` | Seconds taken to process |
| `payload` | Request body (sensitive fields masked as `***`) |
| `request_id` | UUID per request, propagated via context var |
| `service` | Service name from `SERVICE_NAME` env var |
| `host` | Hostname of the container |

Sensitive fields automatically masked in payload: `password`, `token`, `secret`, `authorization`, `api_key`, `access_token`, `refresh_token`.

---

## ClickHouse

### Services

| Service | URL | Purpose |
|---|---|---|
| ClickHouse HTTP | `http://localhost:8123` | SQL over HTTP, `/play` UI |
| ClickHouse Native | `localhost:9000` | Native TCP (used by the Python client) |
| Grafana | `http://localhost:3000` | Dashboard UI (`admin / admin`) |

### Starting the stack

```bash
docker compose up -d
```

The `init.sql` file at `compose/clickhouse/init.sql` is automatically executed on first container start — no manual table creation needed.

### Manually creating the database and table

If you need to recreate the schema (e.g. after wiping the volume):

```bash
# Open the ClickHouse SQL shell
docker compose exec clickhouse clickhouse-client

# Then run:
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
```

Or via HTTP (POST required for write queries):

```bash
curl -X POST "http://localhost:8123" --data "CREATE DATABASE IF NOT EXISTS clickhouse"
curl -X POST "http://localhost:8123" --data "CREATE TABLE IF NOT EXISTS clickhouse.app_logs ..."
```

### Querying logs

Use the browser UI at `http://localhost:8123/play` or `curl`:

**All recent logs:**
```sql
SELECT * FROM clickhouse.app_logs ORDER BY timestamp DESC LIMIT 50;
```

**Only errors:**
```sql
SELECT timestamp, method, endpoint, status_code, request_id, message
FROM clickhouse.app_logs
WHERE level = 'ERROR'
ORDER BY timestamp DESC;
```

**Slow requests (> 1 second):**
```sql
SELECT endpoint, response_time, request_id, timestamp
FROM clickhouse.app_logs
WHERE response_time > 1
ORDER BY response_time DESC;
```

**Request count and average response time per endpoint:**
```sql
SELECT
    endpoint,
    count()              AS hits,
    avg(response_time)   AS avg_time,
    max(response_time)   AS max_time
FROM clickhouse.app_logs
GROUP BY endpoint
ORDER BY hits DESC;
```

**Error rate per endpoint:**
```sql
SELECT
    endpoint,
    countIf(status_code >= 400)                    AS errors,
    count()                                         AS total,
    round(errors / total * 100, 2)                  AS error_pct
FROM clickhouse.app_logs
GROUP BY endpoint
ORDER BY error_pct DESC;
```

**Logs for a specific request (trace by request_id):**
```sql
SELECT *
FROM clickhouse.app_logs
WHERE request_id = 'your-uuid-here';
```

**Row count:**
```sql
SELECT count() FROM clickhouse.app_logs;
```

### Environment variables

Configured via `.env` (loaded by docker-compose into the FastAPI container):

| Variable | Default | Description |
|---|---|---|
| `CLICKHOUSE_HOST` | `clickhouse` | ClickHouse hostname |
| `CLICKHOUSE_PORT` | `8123` | HTTP port |
| `CLICKHOUSE_USER` | `default` | ClickHouse user |
| `CLICKHOUSE_PASSWORD` | _(empty)_ | ClickHouse password |
| `CLICKHOUSE_DB` | `clickhouse` | Database name |
| `SERVICE_NAME` | `book-recommendation` | Appears in every log row |

### Grafana setup (step by step)

The `grafana-clickhouse-datasource` plugin is installed automatically on first boot via `GF_INSTALL_PLUGINS` — no manual plugin installation needed.

#### Step 1 — Open Grafana

Go to `http://localhost:3000` and log in with `admin / admin`.
Grafana may prompt you to change the password — you can skip this.

#### Step 2 — Add ClickHouse as a data source

1. Click **Connections** in the left sidebar
2. Click **Add new connection**
3. Search for **ClickHouse** and click it
4. Click **Add new data source** (top right)
5. Fill in the following fields:

   | Field | Value |
   |---|---|
   | Server address | `clickhouse` |
   | Server port | `9000` |
   | Protocol | `Native` |
   | Username | `default` |
   | Password | _(leave empty)_ |
   | Default database | `clickhouse` |

6. Click **Save & Test** — you should see **"Data source is working"**

#### Step 3 — Create a dashboard

1. Click **Dashboards** in the left sidebar
2. Click **New → New dashboard**
3. Click **Add visualization**
4. Select **ClickHouse** as the data source
5. Switch the query editor to **Code** mode (toggle at top right of the query box)

#### Step 4 — Add panels

Paste each SQL query below into a panel. Set the visualization type as noted.

**Panel: Request rate over time** — visualization: `Time series`
```sql
SELECT
    toStartOfMinute(timestamp) AS time,
    count() AS requests
FROM clickhouse.app_logs
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

**Panel: Error rate over time** — visualization: `Time series`
```sql
SELECT
    toStartOfMinute(timestamp) AS time,
    countIf(status_code >= 400) AS errors,
    countIf(status_code < 400)  AS success
FROM clickhouse.app_logs
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

**Panel: Avg response time per endpoint** — visualization: `Bar chart`
```sql
SELECT
    endpoint,
    round(avg(response_time) * 1000, 2) AS avg_ms
FROM clickhouse.app_logs
WHERE $__timeFilter(timestamp)
GROUP BY endpoint
ORDER BY avg_ms DESC
```

**Panel: Requests by status code** — visualization: `Pie chart`
```sql
SELECT
    toString(status_code) AS status,
    count() AS total
FROM clickhouse.app_logs
WHERE $__timeFilter(timestamp)
GROUP BY status
ORDER BY total DESC
```

**Panel: Recent errors** — visualization: `Table`
```sql
SELECT
    timestamp, method, endpoint,
    status_code, request_id, payload
FROM clickhouse.app_logs
WHERE level = 'ERROR'
    AND $__timeFilter(timestamp)
ORDER BY timestamp DESC
LIMIT 50
```

> `$__timeFilter(timestamp)` is a Grafana macro — it automatically applies the dashboard time range picker to your query.

#### Step 5 — Set time range and auto-refresh

- Top right corner: change the time picker to **Last 15 minutes** or **Last 1 hour**
- Enable **Auto refresh** → set to `10s` for live updates

#### Step 6 — Save the dashboard

Click the **Save** icon (top right), name it `Book Recommendation API`, and click **Save**.

#### Step 7 — Generate traffic to populate panels

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/popular_books
curl -X POST http://localhost:8000/api/recommend_books \
  -H "Content-Type: application/json" \
  -d '{"name_of_book": "The Da Vinci Code", "number_of_recommendations": 5}'
```

Refresh the dashboard — panels should now show data.

---

## Dependencies

- Python 3.10
- FastAPI + uvicorn + starlette
- pandas, numpy
- clickhouse-connect
- Pre-trained pickle models (included in `notebooks/`)

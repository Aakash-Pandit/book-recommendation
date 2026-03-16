# Book Recommendation System

A FastAPI-based REST API that provides book recommendations using collaborative filtering and popularity-based ranking.

## Overview

This project uses a pre-trained similarity model (built in the [notebooks/](notebooks/) directory) to serve two types of book recommendations:

- **Popular books** — top books ranked by rating count and average rating
- **Collaborative filtering** — similar books based on a user-item pivot table and cosine similarity scores

## Project Structure

```
book-recommendation/
├── application/
│   ├── api.py                  # FastAPI routes
│   ├── recommendation.py       # Recommendation logic
│   ├── async_logger.py         # Async queue-based log handler
│   ├── logger.py               # Logger configuration
│   └── middleware_logger.py    # Request/response logging middleware
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
├── run.py                      # App entrypoint (uvicorn)
├── pytest.ini
├── requirements.txt
├── Dockerfile
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
  "popular_books": [
    {"title": "...", "author": "...", "images": "..."}
  ]
}
```

## Running Locally

### With Docker (recommended)

```bash
make build    # Build the Docker image
make start    # Start the container
make stop     # Stop the container
make down     # Stop and remove the container
```

The API will be available at `http://localhost:8000`.

Interactive API docs are available at `http://localhost:8000/docs`.

### Without Docker

```bash
pip install -r requirements.txt
python run.py
```

## Testing

```bash
make test          # Run tests via Docker
pytest tests/ -v   # Run tests locally
```

## Logging

Every request is logged asynchronously via a queue-based worker to avoid blocking request handlers.

Logs are written to:
- **stdout** — visible in the terminal or `docker compose logs -f`
- **`logs/app.log`** — persistent log file (auto-created, git-ignored)

Each log line follows this format:
```
2026-03-16 10:23:01 | INFO     | POST /api/recommend_books | status=200 | 0.012s | API request processed
```

Override the log file path with the `LOG_FILE` env var:
```bash
LOG_FILE=logs/custom.log python run.py
```

## Dependencies

- Python 3.10
- FastAPI + uvicorn + starlette
- pandas, numpy
- Pre-trained pickle models (included in `notebooks/`)

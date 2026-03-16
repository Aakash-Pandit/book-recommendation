import logging
import queue
import time
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# --- AsyncHandler ---

class TestAsyncHandler:

    def test_emit_puts_entry_in_queue(self):
        from application.async_logger import AsyncHandler, log_queue

        with patch.object(log_queue, "put") as mock_put:
            handler = AsyncHandler()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="",
                lineno=0, msg="hello", args=(), exc_info=None
            )
            handler.emit(record)
            mock_put.assert_called_once()

    def test_emit_entry_has_correct_fields(self):
        from application.async_logger import AsyncHandler

        captured = queue.Queue()
        handler = AsyncHandler()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="test message", args=(), exc_info=None
        )
        record.endpoint = "/api/popular_books"
        record.method = "GET"
        record.status_code = 200
        record.response_time = 0.042

        with patch("application.async_logger.log_queue", captured):
            handler.emit(record)

        entry = captured.get_nowait()
        timestamp, level, endpoint, method, status_code, response_time, message = entry

        assert level == "INFO"
        assert endpoint == "/api/popular_books"
        assert method == "GET"
        assert status_code == 200
        assert response_time == 0.042
        assert message == "test message"

    def test_emit_uses_defaults_for_missing_extra_fields(self):
        from application.async_logger import AsyncHandler

        captured = queue.Queue()
        handler = AsyncHandler()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="",
            lineno=0, msg="no extra", args=(), exc_info=None
        )

        with patch("application.async_logger.log_queue", captured):
            handler.emit(record)

        _, _, endpoint, method, status_code, response_time, _ = captured.get_nowait()

        assert endpoint == "-"
        assert method == "-"
        assert status_code == 0
        assert response_time == 0.0


# --- Worker ---

class TestWorker:

    def test_flush_writes_to_stdout(self):
        from application.async_logger import Worker

        worker = Worker(daemon=True)
        batch = [("2026-01-01 00:00:00", "INFO", "/test", "GET", 200, 0.01, "ok")]

        with patch("application.async_logger.sys.stdout", new_callable=StringIO) as mock_stdout:
            worker._flush(batch)
            output = mock_stdout.getvalue()

        assert "INFO" in output
        assert "/test" in output
        assert "GET" in output
        assert "status=200" in output
        assert "0.010s" in output
        assert "ok" in output

    def test_flush_writes_to_log_file(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        worker = Worker(daemon=True)
        batch = [("2026-01-01 00:00:00", "INFO", "/test", "POST", 201, 0.05, "created")]

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush(batch)

        content = log_file.read_text()
        assert "POST" in content
        assert "/test" in content
        assert "status=201" in content

    def test_flush_appends_multiple_entries(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        worker = Worker(daemon=True)
        batch = [
            ("2026-01-01 00:00:00", "INFO", "/a", "GET", 200, 0.01, "first"),
            ("2026-01-01 00:00:01", "INFO", "/b", "POST", 201, 0.02, "second"),
        ]

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush(batch)

        lines = log_file.read_text().splitlines()
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]

    def test_flush_appends_to_existing_file(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        log_file.write_text("existing entry\n")
        worker = Worker(daemon=True)
        batch = [("2026-01-01 00:00:00", "INFO", "/c", "GET", 200, 0.01, "new")]

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush(batch)

        lines = log_file.read_text().splitlines()
        assert lines[0] == "existing entry"
        assert "new" in lines[1]


# --- Middleware integration ---

class TestLoggingMiddleware:

    @pytest.fixture
    def client(self):
        with patch("application.recommendation.popular_df"), \
             patch("application.recommendation.pivot_table"), \
             patch("application.recommendation.books"), \
             patch("application.recommendation.similarity_score"):
            from application.api import application
            yield TestClient(application)

    def test_middleware_calls_logger_on_request(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        mock_logger.info.assert_called_once()

    def test_middleware_logs_correct_endpoint(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/api/popular_books")
        _, kwargs = mock_logger.info.call_args
        assert kwargs["extra"]["endpoint"] == "/api/popular_books"

    def test_middleware_logs_correct_method(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        _, kwargs = mock_logger.info.call_args
        assert kwargs["extra"]["method"] == "GET"

    def test_middleware_logs_status_code(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        _, kwargs = mock_logger.info.call_args
        assert kwargs["extra"]["status_code"] == 200

    def test_middleware_logs_response_time(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        _, kwargs = mock_logger.info.call_args
        assert kwargs["extra"]["response_time"] >= 0

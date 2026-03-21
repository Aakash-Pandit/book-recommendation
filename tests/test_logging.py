import json
import logging
import queue
import time
from io import StringIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# --- AsyncHandler ---

class TestAsyncHandler:

    def test_emit_puts_entry_in_queue(self):
        from application.async_logger import AsyncHandler, log_queue

        with patch.object(log_queue, "put_nowait") as mock_put:
            handler = AsyncHandler()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="",
                lineno=0, msg="hello", args=(), exc_info=None
            )
            handler.emit(record)
            mock_put.assert_called_once()

    def test_emit_entry_has_correct_fields(self):
        from application.async_logger import AsyncHandler, LogEntry

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
        record.request_id = "abc-123"

        with patch("application.async_logger.log_queue", captured):
            handler.emit(record)

        entry: LogEntry = captured.get_nowait()

        assert entry.level == "INFO"
        assert entry.endpoint == "/api/popular_books"
        assert entry.method == "GET"
        assert entry.status_code == 200
        assert entry.response_time == 0.042
        assert entry.request_id == "abc-123"
        assert entry.message == "test message"

    def test_emit_uses_defaults_for_missing_extra_fields(self):
        from application.async_logger import AsyncHandler, LogEntry

        captured = queue.Queue()
        handler = AsyncHandler()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="",
            lineno=0, msg="no extra", args=(), exc_info=None
        )

        with patch("application.async_logger.log_queue", captured):
            handler.emit(record)

        entry: LogEntry = captured.get_nowait()

        assert entry.endpoint == "-"
        assert entry.method == "-"
        assert entry.status_code == 0
        assert entry.response_time == 0.0
        assert entry.payload == "-"

    def test_emit_includes_service_and_host(self):
        from application.async_logger import AsyncHandler, LogEntry

        captured = queue.Queue()
        handler = AsyncHandler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="check metadata", args=(), exc_info=None
        )

        with patch("application.async_logger.log_queue", captured):
            handler.emit(record)

        entry: LogEntry = captured.get_nowait()
        assert entry.service != ""
        assert entry.host != ""

    def test_emit_uses_context_var_request_id_when_not_in_extra(self):
        from application.async_logger import AsyncHandler, LogEntry, request_id_var

        captured = queue.Queue()
        handler = AsyncHandler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="ctx test", args=(), exc_info=None
        )

        token = request_id_var.set("ctx-req-id")
        try:
            with patch("application.async_logger.log_queue", captured):
                handler.emit(record)
        finally:
            request_id_var.reset(token)

        entry: LogEntry = captured.get_nowait()
        assert entry.request_id == "ctx-req-id"

    def test_emit_drops_log_when_queue_full(self):
        from application.async_logger import AsyncHandler

        full_queue = queue.Queue(maxsize=1)
        full_queue.put_nowait("blocker")

        handler = AsyncHandler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="dropped", args=(), exc_info=None
        )

        with patch("application.async_logger.log_queue", full_queue):
            handler.emit(record)  # must not raise or block

        assert full_queue.qsize() == 1  # queue unchanged, log dropped


# --- Worker ---

class TestWorker:

    def _make_entry(self, **kwargs):
        from application.async_logger import LogEntry
        defaults = dict(
            timestamp="2026-01-01 00:00:00",
            level="INFO",
            method="GET",
            endpoint="/test",
            status_code=200,
            response_time=0.01,
            payload="-",
            request_id="req-1",
            message="ok",
            service="book-recommendation",
            host="testhost",
        )
        defaults.update(kwargs)
        return LogEntry(**defaults)

    def test_flush_writes_to_stdout_atomically(self):
        from application.async_logger import Worker

        worker = Worker(daemon=True)
        batch = [self._make_entry(), self._make_entry(message="second")]

        with patch("application.async_logger.sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch("application.async_logger.LOG_FILE", "/dev/null"):
                worker._flush(batch)
            output = mock_stdout.getvalue()

        assert output.count("INFO") == 2
        assert "req-1" in output
        assert "ok" in output
        assert "second" in output

    def test_flush_stdout_line_format(self):
        from application.async_logger import Worker

        worker = Worker(daemon=True)
        batch = [self._make_entry()]

        with patch("application.async_logger.sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch("application.async_logger.LOG_FILE", "/dev/null"):
                worker._flush(batch)
            output = mock_stdout.getvalue()

        assert "INFO" in output
        assert "/test" in output
        assert "GET" in output
        assert "status=200" in output
        assert "0.010s" in output
        assert "req-1" in output

    def test_flush_writes_json_to_log_file(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        worker = Worker(daemon=True)
        batch = [self._make_entry(method="POST", status_code=201, message="created")]

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush(batch)

        line = json.loads(log_file.read_text().strip())
        assert line["method"] == "POST"
        assert line["endpoint"] == "/test"
        assert line["status_code"] == 201
        assert line["message"] == "created"
        assert line["service"] == "book-recommendation"
        assert line["host"] == "testhost"

    def test_flush_appends_multiple_entries(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        worker = Worker(daemon=True)
        batch = [
            self._make_entry(endpoint="/a", message="first"),
            self._make_entry(endpoint="/b", method="POST", status_code=201, message="second"),
        ]

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush(batch)

        lines = [json.loads(l) for l in log_file.read_text().splitlines()]
        assert len(lines) == 2
        assert lines[0]["message"] == "first"
        assert lines[1]["message"] == "second"

    def test_flush_appends_to_existing_file(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "test.log"
        log_file.write_text(json.dumps({"message": "existing"}) + "\n")
        worker = Worker(daemon=True)

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.sys.stdout", new_callable=StringIO):
                worker._flush([self._make_entry(message="new")])

        lines = [json.loads(l) for l in log_file.read_text().splitlines()]
        assert lines[0]["message"] == "existing"
        assert lines[1]["message"] == "new"

    def test_rotation_triggered_when_file_exceeds_limit(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "app.log"
        log_file.write_bytes(b"x" * 100)
        worker = Worker(daemon=True)

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.MAX_FILE_BYTES", 50):
                worker._rotate_if_needed()

        assert not log_file.exists()
        assert (tmp_path / "app.log.1").exists()

    def test_rotation_not_triggered_when_file_under_limit(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "app.log"
        log_file.write_bytes(b"x" * 10)
        worker = Worker(daemon=True)

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.MAX_FILE_BYTES", 1000):
                worker._rotate_if_needed()

        assert log_file.exists()
        assert not (tmp_path / "app.log.1").exists()

    def test_rotation_shifts_existing_backups(self, tmp_path):
        from application.async_logger import Worker

        log_file = tmp_path / "app.log"
        log_file.write_bytes(b"x" * 100)
        (tmp_path / "app.log.1").write_bytes(b"old-1")
        (tmp_path / "app.log.2").write_bytes(b"old-2")
        worker = Worker(daemon=True)

        with patch("application.async_logger.LOG_FILE", str(log_file)):
            with patch("application.async_logger.MAX_FILE_BYTES", 50):
                worker._rotate_if_needed()

        assert (tmp_path / "app.log.1").exists()
        assert (tmp_path / "app.log.2").read_bytes() == b"old-1"
        assert (tmp_path / "app.log.3").read_bytes() == b"old-2"


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

    def test_middleware_logs_query_string_in_endpoint(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/api/popular_books?limit=10")
        _, kwargs = mock_logger.info.call_args
        assert "limit=10" in kwargs["extra"]["endpoint"]

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

    def test_middleware_logs_request_id(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        _, kwargs = mock_logger.info.call_args
        assert "request_id" in kwargs["extra"]
        assert len(kwargs["extra"]["request_id"]) == 36  # UUID format

    def test_middleware_sets_context_var(self, client):
        from application.async_logger import request_id_var
        observed = []

        with patch("application.middleware_logger.logger") as mock_logger:
            mock_logger.info.side_effect = lambda *a, **kw: observed.append(request_id_var.get())
            client.get("/")

        assert len(observed) == 1
        assert len(observed[0]) == 36  # UUID set in context during the request

    def test_middleware_logs_payload_for_post(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            with patch("application.api.top_recommend_books", return_value=[]):
                client.post(
                    "/api/recommend_books",
                    json={"name_of_book": "Dune", "number_of_recommendations": 3},
                )
        _, kwargs = mock_logger.info.call_args
        assert "Dune" in kwargs["extra"]["payload"]

    def test_middleware_masks_sensitive_fields(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            with patch("application.api.top_recommend_books", return_value=[]):
                client.post(
                    "/api/recommend_books",
                    json={"name_of_book": "Dune", "password": "s3cr3t"},
                )
        _, kwargs = mock_logger.info.call_args
        assert "s3cr3t" not in kwargs["extra"]["payload"]
        assert "***" in kwargs["extra"]["payload"]

    def test_middleware_uses_warning_for_4xx(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.post("/api/recommend_books", json={})
        mock_logger.warning.assert_called_once()

    def test_middleware_uses_info_for_2xx(self, client):
        with patch("application.middleware_logger.logger") as mock_logger:
            client.get("/")
        mock_logger.info.assert_called_once()


# --- Sensitive field masking (unit) ---

class TestParseBody:

    def test_masks_password_field(self):
        from application.middleware_logger import _parse_body
        raw = json.dumps({"username": "alice", "password": "secret"}).encode()
        result = _parse_body(raw)
        parsed = json.loads(result)
        assert parsed["password"] == "***"
        assert parsed["username"] == "alice"

    def test_masks_token_field(self):
        from application.middleware_logger import _parse_body
        raw = json.dumps({"token": "abc123"}).encode()
        result = json.loads(_parse_body(raw))
        assert result["token"] == "***"

    def test_non_sensitive_fields_unchanged(self):
        from application.middleware_logger import _parse_body
        raw = json.dumps({"name_of_book": "Dune"}).encode()
        result = json.loads(_parse_body(raw))
        assert result["name_of_book"] == "Dune"

    def test_empty_body_returns_dash(self):
        from application.middleware_logger import _parse_body
        assert _parse_body(b"") == "-"

    def test_non_json_body_returned_as_text(self):
        from application.middleware_logger import _parse_body
        assert _parse_body(b"plain text") == "plain text"

    def test_body_truncated_at_max_size(self):
        from application.middleware_logger import _parse_body, MAX_BODY_LOG_SIZE
        raw = b"x" * (MAX_BODY_LOG_SIZE + 500)
        result = _parse_body(raw)
        assert len(result) <= MAX_BODY_LOG_SIZE

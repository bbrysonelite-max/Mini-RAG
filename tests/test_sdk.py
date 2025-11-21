import json
from pathlib import Path

import pytest

from clients.sdk import MiniRAGClient, MiniRAGError


class DummyResponse:
    """Lightweight stand-in for httpx.Response used by the SDK tests."""

    def __init__(self, status_code=200, json_data=None, text=None, reason="OK"):
        self.status_code = status_code
        self._json_data = json_data
        if text is None and json_data is not None:
            text = json.dumps(json_data)
        self.text = text or ""
        self.content = self.text.encode("utf-8")
        self.reason_phrase = reason

    def json(self):
        if self._json_data is None:
            raise json.JSONDecodeError("No JSON payload", self.text, 0)
        return self._json_data


class DummyClient:
    """Captures the payload that the SDK sends without issuing HTTP calls."""

    def __init__(self, response):
        self._response = response
        self.calls = []
        self.closed = False

    def post(self, path, *, data=None, files=None, json=None):
        self.calls.append(
            {
                "method": "post",
                "path": path,
                "data": data,
                "files": files,
                "json": json,
            }
        )
        return self._response

    def get(self, path):
        self.calls.append({"method": "get", "path": path})
        return self._response

    def close(self):
        self.closed = True


def test_ask_posts_form_payload_and_returns_json():
    response = DummyResponse(json_data={"answer": "hi"})
    dummy_client = DummyClient(response=response)
    client = MiniRAGClient(base_url="https://api.example.com")
    client._client = dummy_client

    result = client.ask("hello", k=5, workspace_id="ws-123")

    assert result == {"answer": "hi"}
    assert dummy_client.calls == [
        {
            "method": "post",
            "path": "/api/v1/ask",
            "data": {"query": "hello", "k": "5", "workspace_id": "ws-123"},
            "files": None,
            "json": None,
        }
    ]
    client.close()


def test_ingest_files_sends_multipart_payload(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("hello world")

    response = DummyResponse(json_data={"status": "ok"})
    dummy_client = DummyClient(response=response)
    client = MiniRAGClient(base_url="https://api.example.com")
    client._client = dummy_client

    result = client.ingest_files([sample_file], language="en")

    assert result == {"status": "ok"}
    call = dummy_client.calls[0]
    assert call["path"] == "/api/v1/ingest/files"
    assert call["data"] == {"language": "en"}
    assert call["files"] == [
        ("files", ("sample.txt", sample_file.read_bytes()))
    ]
    client.close()


def test_handle_response_raises_sdk_error_on_http_failure():
    client = MiniRAGClient(base_url="https://api.example.com")
    failing_response = DummyResponse(status_code=429, text="rate limited", reason="Too Many Requests")

    with pytest.raises(MiniRAGError) as exc_info:
        client._handle_response(failing_response)

    assert "429" in str(exc_info.value)
    client.close()


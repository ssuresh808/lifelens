"""Tests for the secure baseline: rate limiting, daily budget, security headers."""

import base64

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
FAKE_IMG = base64.b64encode(b"x" * 200).decode()
SCAN_BODY = {"mode": "auto", "media_type": "image/jpeg", "image_base64": FAKE_IMG}


@pytest.fixture
def fake_upstream(monkeypatch):
    """A working API key plus a stub upstream that always returns a valid scan."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    body = (
        '{"category": "Test", "title": "ok", "confidence": "high", '
        '"summary": "fine."}'
    )

    class _Resp:
        status_code = 200

        def json(self):
            return {"content": [{"type": "text", "text": body}]}

    async def post(self, *args, **kwargs):
        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


def test_burst_over_limit_returns_429_with_retry_after(fake_upstream):
    """More than BURST_LIMIT requests in the burst window are rejected fast."""
    last = None
    for _ in range(main.BURST_LIMIT + 1):
        last = client.post("/scan", json=SCAN_BODY)
    assert last.status_code == 429
    assert int(last.headers["Retry-After"]) > 0


def test_sustained_limit_returns_429_with_retry_after(fake_upstream):
    """Reaching the hourly cap (without tripping the burst window first) is a 429."""
    import time

    # Seed the hourly window full, but with hits older than the burst window so
    # only the sustained limit is in play.
    main._hits["testclient"] = [time.time() - 120] * main.RATE_LIMIT
    r = client.post("/scan", json=SCAN_BODY)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


def test_under_limit_requests_pass(fake_upstream):
    """A normal request well under the limits succeeds."""
    r = client.post("/scan", json=SCAN_BODY)
    assert r.status_code == 200


def test_daily_budget_exhausted_returns_503_with_retry_after(fake_upstream, monkeypatch):
    """Once the service-wide daily budget is spent, further calls get a 503."""
    monkeypatch.setattr(main, "DAILY_BUDGET", 2)
    assert client.post("/scan", json=SCAN_BODY).status_code == 200
    assert client.post("/scan", json=SCAN_BODY).status_code == 200
    r = client.post("/scan", json=SCAN_BODY)
    assert r.status_code == 503
    assert 0 < int(r.headers["Retry-After"]) <= 86400


def test_failed_validation_does_not_spend_budget(fake_upstream, monkeypatch):
    """A rejected request (bad base64) must not consume the daily budget."""
    monkeypatch.setattr(main, "DAILY_BUDGET", 1)
    bad = {"mode": "auto", "media_type": "image/jpeg", "image_base64": "!!!bad!!!" * 20}
    assert client.post("/scan", json=bad).status_code == 400
    # the single budget unit is still available for a real request
    assert client.post("/scan", json=SCAN_BODY).status_code == 200

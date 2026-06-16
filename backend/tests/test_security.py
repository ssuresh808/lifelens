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


SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Content-Security-Policy",
)


def test_security_headers_present_on_responses():
    r = client.get("/health")
    assert r.status_code == 200
    for h in SECURITY_HEADERS:
        assert h in r.headers, h
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_security_headers_on_error_responses(fake_upstream):
    """A 429 must still carry both security headers and its Retry-After."""
    last = None
    for _ in range(main.BURST_LIMIT + 1):
        last = client.post("/scan", json=SCAN_BODY)
    assert last.status_code == 429
    assert "Retry-After" in last.headers
    assert last.headers["X-Content-Type-Options"] == "nosniff"


def test_paused_blocks_scan_with_503(fake_upstream, monkeypatch):
    monkeypatch.setenv("LIFELENS_PAUSED", "1")
    r = client.post("/scan", json=SCAN_BODY)
    assert r.status_code == 503
    assert "paused" in r.json()["detail"].lower()


def test_paused_blocks_chat_before_anything_else(monkeypatch):
    # No API key set: the pause must short-circuit before the key check.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LIFELENS_PAUSED", "true")
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hi"}]})
    assert r.status_code == 503


def test_health_reports_paused_state(monkeypatch):
    monkeypatch.setenv("LIFELENS_PAUSED", "yes")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("paused") is True


def test_not_paused_by_default(fake_upstream):
    r = client.post("/scan", json=SCAN_BODY)
    assert r.status_code == 200


def test_cors_allows_configured_origin():
    """The configured frontend origin is still permitted after tightening headers."""
    r = client.options(
        "/scan",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

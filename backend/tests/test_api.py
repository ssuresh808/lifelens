"""Tests for schema validation, prompt construction, and endpoint guards."""

import base64
import ssl

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ScanRequest, ScanResult
from app.prompts import MODE_BRIEFS, build_system_prompt

client = TestClient(app)
FAKE_IMG = base64.b64encode(b"x" * 200).decode()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_every_mode_has_a_brief_and_contract():
    for mode in ("auto", "document", "fixit", "nutrition", "translate"):
        prompt = build_system_prompt(mode)
        assert MODE_BRIEFS[mode] in prompt
        assert '"confidence"' in prompt  # output contract present


def test_plant_mode_is_gone():
    assert "plant" not in MODE_BRIEFS
    with pytest.raises(ValueError):
        ScanRequest(mode="plant", image_base64=FAKE_IMG)


def test_unknown_mode_falls_back_to_auto():
    assert build_system_prompt("nonsense") == build_system_prompt("auto")


def test_request_rejects_bad_media_type():
    with pytest.raises(ValueError):
        ScanRequest(mode="auto", media_type="application/pdf", image_base64=FAKE_IMG)


def test_request_rejects_invalid_mode():
    with pytest.raises(ValueError):
        ScanRequest(mode="astrology", image_base64=FAKE_IMG)


def test_result_schema_round_trip():
    r = ScanResult(
        category="Plant health",
        title="Overwatered pothos",
        confidence="high",
        summary="Yellow lower leaves and soggy soil point to overwatering.",
        steps=["Let soil dry", "Check drainage"],
    )
    assert r.warnings == [] and r.followUp == []


def test_scan_rejects_invalid_base64():
    r = client.post(
        "/scan",
        json={"mode": "auto", "media_type": "image/jpeg", "image_base64": "!!!not-base64!!!" * 20},
    )
    assert r.status_code == 400


def test_scan_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post(
        "/scan",
        json={"mode": "auto", "media_type": "image/jpeg", "image_base64": FAKE_IMG},
    )
    assert r.status_code == 500
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


@pytest.mark.parametrize(
    "exc",
    [httpx.ConnectError("network down"), ssl.SSLError("bad record mac")],
    ids=["httpx-error", "raw-ssl-error"],
)
def test_scan_returns_502_when_upstream_unreachable(monkeypatch, exc):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    async def boom(self, *args, **kwargs):
        raise exc

    monkeypatch.setattr(httpx.AsyncClient, "post", boom)
    r = client.post(
        "/scan",
        json={"mode": "auto", "media_type": "image/jpeg", "image_base64": FAKE_IMG},
    )
    assert r.status_code == 502


def test_request_accepts_note_and_web_search():
    r = ScanRequest(mode="auto", image_base64=FAKE_IMG, note="what breed?", web_search=True)
    assert r.web_search and r.note == "what breed?"


def test_request_rejects_oversized_note():
    with pytest.raises(ValueError):
        ScanRequest(mode="auto", image_base64=FAKE_IMG, note="x" * 600)


def test_web_search_clause_only_when_enabled():
    assert "web_search" in build_system_prompt("auto", web_search=True)
    assert "web_search" not in build_system_prompt("auto", web_search=False)


def test_result_accepts_sources():
    r = ScanResult(
        category="Landmark",
        title="Golden Gate Bridge",
        confidence="high",
        summary="A suspension bridge in San Francisco.",
        sources=[{"title": "Official site", "url": "https://example.org"}],
    )
    assert r.sources[0].url.startswith("https")

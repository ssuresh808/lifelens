"""Tests for the /chat contract and Berry prompts."""

import base64
import json as jsonlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChatMessage, ChatReply, ChatRequest
from app.prompts import build_chat_prompt

FAKE_IMG = base64.b64encode(b"x" * 200).decode()

client = TestClient(app)


class _FakeResp:
    status_code = 200

    def __init__(self, text):
        self._text = text

    def json(self):
        return {"content": [{"type": "text", "text": self._text}]}


def _fake_post(reply_text):
    async def post(self, *args, **kwargs):
        return _FakeResp(reply_text)
    return post


def test_chat_request_minimal():
    r = ChatRequest(messages=[{"role": "user", "text": "hi"}])
    assert r.tab == "ask" and r.web_search is False


def test_chat_request_cook_tab():
    r = ChatRequest(tab="cook", messages=[{"role": "user", "text": "hi"}])
    assert r.tab == "cook"


def test_chat_request_rejects_bad_tab():
    with pytest.raises(ValueError):
        ChatRequest(tab="garden", messages=[{"role": "user", "text": "hi"}])


def test_chat_request_rejects_empty_history():
    with pytest.raises(ValueError):
        ChatRequest(messages=[])


def test_chat_request_caps_history_at_30():
    msgs = [{"role": "user", "text": "hi"}] * 31
    with pytest.raises(ValueError):
        ChatRequest(messages=msgs)


def test_chat_request_accepts_exactly_30_messages():
    msgs = [{"role": "user", "text": "hi"}] * 30
    assert len(ChatRequest(messages=msgs).messages) == 30


def test_image_only_on_user_messages():
    with pytest.raises(ValueError):
        ChatMessage(role="assistant", text="x", image_base64=FAKE_IMG, media_type="image/jpeg")


def test_image_requires_valid_media_type():
    with pytest.raises(ValueError):
        ChatMessage(role="user", text="x", image_base64=FAKE_IMG, media_type="application/pdf")


def test_at_most_two_images_per_request():
    img = {"role": "user", "text": "x", "image_base64": FAKE_IMG, "media_type": "image/jpeg"}
    with pytest.raises(ValueError):
        ChatRequest(messages=[img, img, img])


def test_chat_reply_round_trip_with_dishes_and_recipe():
    reply = ChatReply(
        message="Here is your menu!",
        dishes=[{"id": "tikka-rice", "name": "Chicken Tikka Rice", "cuisine": "Indian",
                 "minutes": 25, "serves": 2, "difficulty": "easy",
                 "have": ["chicken", "rice"], "nice_to_add": ["cilantro"]}],
        recipe={"name": "Chicken Tikka Rice", "cuisine": "Indian", "minutes": 25,
                "serves": 2, "ingredients": [{"item": "chicken thighs", "amount": "400 g"}],
                "steps": ["Marinate the chicken."]},
        chips=["make it spicier"],
        goal="Dinner on the table in 25 minutes.",
        sources=[{"title": "x", "url": "https://example.org"}],
    )
    assert reply.dishes[0].minutes == 25
    assert reply.recipe.steps == ["Marinate the chicken."]


def test_chat_prompt_has_persona_contract_and_safety():
    for tab in ("cook", "ask"):
        p = build_chat_prompt(tab)
        assert "Berry" in p
        assert '"message"' in p            # JSON contract present
        assert "never use em dashes" in p.lower()
        assert "refuse" in p.lower()       # safety section present


def test_cook_prompt_covers_the_flow():
    p = build_chat_prompt("cook")
    for needle in ("spices", "5 to 10", "cuisine", "serves", "feasible"):
        assert needle in p, needle


def test_ask_prompt_covers_goal_and_steps():
    p = build_chat_prompt("ask")
    assert "goal" in p and "numbered steps" in p.lower()


def test_chat_web_search_clause_only_when_enabled():
    assert "web_search" in build_chat_prompt("ask", web_search=True)
    assert "web_search" not in build_chat_prompt("ask", web_search=False)


def test_unknown_tab_falls_back_to_ask():
    assert build_chat_prompt("garden") == build_chat_prompt("ask")


def test_chat_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    body = jsonlib.dumps({"message": "Hi! What's in your kitchen?", "chips": ["snap a photo"]})
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post(body))
    r = client.post("/chat", json={"tab": "cook", "messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 200
    data = r.json()
    assert data["message"].startswith("Hi!") and data["dishes"] == [] and data["recipe"] is None


def test_chat_unparseable_reply_is_502(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post("no json here"))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 502


def test_chat_network_error_is_502(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    async def boom(self, *args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx.AsyncClient, "post", boom)
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 502


def test_chat_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 500
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_chat_rejects_oversized_image(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    big = base64.b64encode(b"x" * (6 * 1024 * 1024)).decode()
    r = client.post("/chat", json={"messages": [
        {"role": "user", "text": "x", "image_base64": big, "media_type": "image/jpeg"}]})
    assert r.status_code == 413

"""Tests for the /chat contract and Berry prompts."""

import base64
import json as jsonlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChatMessage, ChatReply, ChatRequest, DishCard, Recipe
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


def test_cook_prompt_explains_tapped_preferences():
    p = build_chat_prompt("cook")
    assert "Meal preferences selected in the app" in p
    assert "never ask again" in p


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


def test_chat_merges_consecutive_same_role_messages(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    seen = {}
    body = jsonlib.dumps({"message": "ok"})

    async def post(self, url, json=None, headers=None):
        seen["payload"] = json
        return _FakeResp(body)

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    r = client.post("/chat", json={"messages": [
        {"role": "user", "text": "full recipe for tacos"},
        {"role": "user", "text": "full recipe for tofu tacos"},
    ]})
    assert r.status_code == 200
    roles = [m["role"] for m in seen["payload"]["messages"]]
    assert roles == ["user"]
    texts = [b["text"] for b in seen["payload"]["messages"][0]["content"]]
    assert texts == ["full recipe for tacos", "full recipe for tofu tacos"]


def test_chat_tolerates_literal_newlines_in_strings(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post('{"message": "line one\nline two"}'))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hi"}]})
    assert r.status_code == 200
    assert "line two" in r.json()["message"]


# Berry's words must always reach the user: any non-empty reply is salvaged.

def test_chat_plain_text_reply_is_salvaged(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post("Try the tofu tacos, they rock!"))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 200
    assert r.json()["message"] == "Try the tofu tacos, they rock!"


def test_chat_trailing_commas_are_repaired(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post('{"message": "ok", "chips": ["a",],}'))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 200
    assert r.json()["chips"] == ["a"]


def test_chat_invalid_optional_payload_keeps_message(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post('{"message": "menu time", "dishes": "whoops"}'))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "menu time"
    assert body["dishes"] == []


def test_chat_truncated_json_is_regex_salvaged(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post('{"message": "half a reply", "dishes": [{"name": "x"'))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 200
    assert r.json()["message"] == "half a reply"


def test_chat_empty_reply_is_502(monkeypatch):
    from app.main import _hits
    _hits.clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post(""))
    r = client.post("/chat", json={"messages": [{"role": "user", "text": "hello"}]})
    assert r.status_code == 502


def test_dishcard_coerces_sloppy_model_output():
    d = DishCard(name="Tacos", minutes="25 min", serves=None)
    assert d.minutes == 25 and d.serves == 0 and d.id == ""


def test_recipe_accepts_plain_string_ingredients():
    rec = Recipe(name="Bowl", ingredients=["eggs", {"item": "milk", "amount": 2}])
    assert rec.ingredients[0].item == "eggs"
    assert rec.ingredients[1].amount == "2"


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


def test_chat_rejects_assistant_first():
    r = client.post("/chat", json={"messages": [{"role": "assistant", "text": "hi"}]})
    assert r.status_code == 422


def test_chat_preserves_role_alternation(monkeypatch):
    """A blank assistant turn must become '...' so roles stay alternating."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    captured = {}

    async def post(self, url, json=None, headers=None):
        captured.update(json)
        return _FakeResp(jsonlib.dumps({"message": "ok"}))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    r = client.post("/chat", json={"messages": [
        {"role": "user", "text": "hi"},
        {"role": "assistant", "text": ""},
        {"role": "user", "text": "still there?"},
    ]})
    assert r.status_code == 200
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["user", "assistant", "user"]
    # blank assistant turn must carry the placeholder text, not empty
    asst_content = captured["messages"][1]["content"]
    assert any(b.get("text") == "..." for b in asst_content)


def test_chat_payload_shape_and_web_search_tool(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    captured = {}

    async def post(self, url, json=None, headers=None):
        captured.update(json)
        return _FakeResp(jsonlib.dumps({"message": "ok"}))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    r = client.post("/chat", json={"tab": "cook", "web_search": True,
                                   "messages": [{"role": "user", "text": "dinner ideas"}]})
    assert r.status_code == 200
    assert "Berry" in captured["system"]
    assert captured["messages"][0]["role"] == "user"
    assert captured["messages"][0]["content"][0] == {"type": "text", "text": "dinner ideas"}
    assert captured["tools"] == [{"type": "web_search_20250305", "name": "web_search"}]


def test_chat_parses_reply_that_follows_tool_use_blocks(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    class _ToolResp:
        status_code = 200

        def json(self):
            return {"content": [
                {"type": "server_tool_use", "name": "web_search", "input": {}},
                {"type": "text", "text": jsonlib.dumps({"message": "found it", "sources": [
                    {"title": "x", "url": "https://example.org"}]})},
            ]}

    async def post(self, *args, **kwargs):
        return _ToolResp()

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    r = client.post("/chat", json={"web_search": True,
                                   "messages": [{"role": "user", "text": "look this up"}]})
    assert r.status_code == 200
    assert r.json()["sources"][0]["url"] == "https://example.org"

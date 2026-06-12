"""Tests for the /chat contract and Berry prompts."""

import base64

import pytest

from app.models import ChatMessage, ChatReply, ChatRequest

FAKE_IMG = base64.b64encode(b"x" * 200).decode()


def test_chat_request_minimal():
    r = ChatRequest(messages=[{"role": "user", "text": "hi"}])
    assert r.tab == "ask" and r.web_search is False


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
    assert reply.dishes[0].minutes == 25 and reply.recipe.steps

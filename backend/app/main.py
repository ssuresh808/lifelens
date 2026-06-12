"""LifeLens API — server-side proxy to the Anthropic API.

Keeps the API key off the client, validates inputs, enforces rate limits,
and guarantees the response matches the ScanResult schema.
"""

import base64
import binascii
import json
import logging
import os
import time
from collections import defaultdict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .models import ChatReply, ChatRequest, ScanRequest, ScanResult
from .prompts import build_chat_prompt, build_system_prompt

logger = logging.getLogger("lifelens")
logging.basicConfig(level=logging.INFO)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("LIFELENS_MODEL", "claude-sonnet-4-6")
CHAT_MODEL = os.getenv("LIFELENS_CHAT_MODEL", "claude-opus-4-8")
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB decoded
RATE_LIMIT = 20          # requests
RATE_WINDOW = 60 * 60    # per hour, per client IP

app = FastAPI(title="LifeLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("LIFELENS_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limited(ip: str) -> bool:
    now = time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < RATE_WINDOW]
    if len(_hits[ip]) >= RATE_LIMIT:
        return True
    _hits[ip].append(now)
    return False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL}


async def _complete(payload: dict, api_key: str) -> str:
    """POST to the model API; return the joined text blocks. Raises HTTPException."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                ANTHROPIC_URL,
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
    except (httpx.HTTPError, OSError) as exc:
        # OSError covers ssl.SSLError, which httpx can leak unwrapped
        logger.error("Upstream connection failed: %r", exc)
        raise HTTPException(502, "Could not reach the AI model. Please try again.")

    if resp.status_code != 200:
        logger.error("Upstream error %s: %s", resp.status_code, resp.text[:500])
        raise HTTPException(502, "The AI model is unavailable right now.")

    return "".join(
        block.get("text", "")
        for block in resp.json().get("content", [])
        if block.get("type") == "text"
    )


def _extract_json(text: str) -> str:
    """The model occasionally wraps JSON in fences or adds preamble.

    Returns "" if no JSON object is found."""
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else ""


@app.post("/scan", response_model=ScanResult)
async def scan(req: ScanRequest, request: Request) -> ScanResult:
    ip = request.client.host if request.client else "unknown"
    if _rate_limited(ip):
        raise HTTPException(429, "Rate limit reached. Try again in an hour.")

    try:
        raw = base64.b64decode(req.image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "image_base64 is not valid base64.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image exceeds the 5 MB limit.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "Server is missing ANTHROPIC_API_KEY.")

    payload = {
        "model": MODEL,
        "max_tokens": 4096,
        "system": build_system_prompt(req.mode, req.web_search),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": req.media_type,
                            "data": req.image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Analyze this image. My note/question: {req.note.strip()}"
                            if req.note.strip()
                            else "Analyze this image."
                        ),
                    },
                ],
            }
        ],
    }
    if req.web_search:
        payload["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    text = await _complete(payload, api_key)
    clean = _extract_json(text)

    try:
        return ScanResult(**json.loads(clean))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Schema parse failure: %s | raw: %s", exc, clean[:300])
        raise HTTPException(502, "The model returned an unreadable result. Please rescan.")


@app.post("/chat", response_model=ChatReply)
async def chat(req: ChatRequest, request: Request) -> ChatReply:
    ip = request.client.host if request.client else "unknown"
    if _rate_limited(ip):
        raise HTTPException(429, "Rate limit reached. Try again in an hour.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "Server is missing ANTHROPIC_API_KEY.")

    messages = []
    for m in req.messages:
        content: list[dict] = []
        if m.image_base64:
            try:
                raw = base64.b64decode(m.image_base64, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(400, "image_base64 is not valid base64.")
            if len(raw) > MAX_IMAGE_BYTES:
                raise HTTPException(413, "Image exceeds the 5 MB limit.")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": m.media_type, "data": m.image_base64},
            })
        if m.text.strip():
            content.append({"type": "text", "text": m.text.strip()})
        if not content:
            raise HTTPException(400, "A message needs text or an image.")
        messages.append({"role": m.role, "content": content})

    payload = {
        "model": CHAT_MODEL,
        "max_tokens": 4096,
        "system": build_chat_prompt(req.tab, req.web_search),
        "messages": messages,
    }
    if req.web_search:
        payload["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    text = await _complete(payload, api_key)
    clean = _extract_json(text)

    try:
        return ChatReply(**json.loads(clean))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Chat parse failure: %s | raw: %s", exc, clean[:300])
        raise HTTPException(502, "Berry got tongue-tied. Please send that again.")

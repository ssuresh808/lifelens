"""LifeLens API — server-side proxy to the Anthropic API.

Keeps the API key off the client, validates inputs, enforces rate limits,
and guarantees the response matches the ScanResult schema.
"""

import base64
import binascii
import json
import logging
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

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

# Layered per-IP rate limits. The burst window catches rapid-fire abuse; the
# longer window caps sustained use. Whichever trips first wins.
RATE_LIMIT = int(os.getenv("LIFELENS_RATE_LIMIT", "20"))            # sustained requests
RATE_WINDOW = int(os.getenv("LIFELENS_RATE_WINDOW", str(60 * 60)))  # per hour, per IP
BURST_LIMIT = int(os.getenv("LIFELENS_BURST_LIMIT", "5"))           # burst requests
BURST_WINDOW = int(os.getenv("LIFELENS_BURST_WINDOW", "60"))        # per minute, per IP

# Service-wide cost circuit breaker: the Anthropic API has no per-request hard
# ceiling, so cap total upstream calls per UTC day across all callers.
DAILY_BUDGET = int(os.getenv("LIFELENS_DAILY_BUDGET", "1000"))

app = FastAPI(title="LifeLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("LIFELENS_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],  # the only header the client sends
)

# Sent on every response, including errors. The API only ever returns JSON, so
# its own CSP locks rendering down entirely; HSTS hardens the HTTPS the platform
# already terminates. The browser-facing frontend sets its own headers (vercel.json).
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response

_hits: dict[str, list[float]] = defaultdict(list)
_daily: dict[str, int] = defaultdict(int)


def _retry_after(ip: str) -> int:
    """Seconds the caller must wait, or 0 if the request is allowed.

    Records the hit only when the request is allowed, so a rejected caller is
    not pushed further past the limit by their own retries."""
    now = time.time()
    hits = _hits[ip] = [t for t in _hits[ip] if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        return math.ceil(RATE_WINDOW - (now - hits[0]))
    recent = [t for t in hits if now - t < BURST_WINDOW]
    if len(recent) >= BURST_LIMIT:
        return math.ceil(BURST_WINDOW - (now - recent[0]))
    hits.append(now)
    return 0


def _budget_retry_after() -> int:
    """Seconds until the daily budget resets if it's spent, else 0."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for day in [d for d in _daily if d != today]:
        del _daily[day]  # keep only today's counter
    if _daily[today] >= DAILY_BUDGET:
        now = datetime.now(timezone.utc)
        reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return math.ceil((reset - now).total_seconds())
    return 0


def _spend_budget() -> None:
    _daily[datetime.now(timezone.utc).strftime("%Y-%m-%d")] += 1


def _enforce_limits(request: Request) -> None:
    """Reject the request if the daily budget is spent (503) or the caller is
    rate limited (429). Both responses carry a Retry-After header."""
    wait = _budget_retry_after()
    if wait:
        raise HTTPException(
            503,
            "LifeLens has reached its daily capacity. Please try again tomorrow.",
            headers={"Retry-After": str(wait)},
        )
    ip = request.client.host if request.client else "unknown"
    wait = _retry_after(ip)
    if wait:
        raise HTTPException(
            429, "Rate limit reached. Please slow down.", headers={"Retry-After": str(wait)}
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL}


async def _complete(payload: dict, api_key: str) -> str:
    """POST to the model API; return the joined text blocks. Raises HTTPException."""
    _spend_budget()  # an upstream call is the unit of cost we cap
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


def _salvage_chat_reply(text: str) -> ChatReply:
    """Berry's words must reach the user even when his JSON wrapper is mangled.

    Tries, in order: full parse, trailing-comma repair, message-only from the
    parsed dict, regex extraction of the message string, and finally the raw
    text itself. Only an empty reply is an error."""
    clean = _extract_json(text)
    for candidate in (clean, re.sub(r",\s*([}\]])", r"\1", clean)) if clean else ():
        try:
            data = json.loads(candidate, strict=False)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            break
        try:
            return ChatReply(**data)
        except (TypeError, ValueError):
            msg = data.get("message")
            if isinstance(msg, str) and msg.strip():
                logger.warning("Chat reply salvaged to message only | raw: %s", candidate[:800])
                return ChatReply(message=msg.strip())
            break
    m = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', clean or text)
    if m:
        msg = m.group(1).replace('\\"', '"').replace("\\n", "\n").strip()
        if msg:
            logger.warning("Chat reply message regex-salvaged | raw: %s", (clean or text)[:800])
            return ChatReply(message=msg)
    fallback = text.strip()
    if fallback:
        logger.warning("Chat reply used as plain text | raw: %s", text[:800])
        return ChatReply(message=fallback)
    raise HTTPException(502, "Berry got tongue-tied. Please send that again.")


@app.post("/scan", response_model=ScanResult)
async def scan(req: ScanRequest, request: Request) -> ScanResult:
    _enforce_limits(request)

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
        # strict=False tolerates literal newlines the model sometimes leaves in strings
        return ScanResult(**json.loads(clean, strict=False))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Schema parse failure: %s | raw: %s", exc, clean[:300])
        raise HTTPException(502, "The model returned an unreadable result. Please rescan.")


@app.post("/chat", response_model=ChatReply)
async def chat(req: ChatRequest, request: Request) -> ChatReply:
    _enforce_limits(request)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "Server is missing ANTHROPIC_API_KEY.")

    messages: list[dict] = []
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
        text_body = m.text.strip()
        if text_body:
            content.append({"type": "text", "text": text_body})
        if not content:
            if m.role == "assistant":
                # preserve role alternation; use placeholder rather than dropping
                content.append({"type": "text", "text": "..."})
            else:
                raise HTTPException(400, "A message needs text or an image.")
        # After a failed turn the client may resend two user messages in a row;
        # the model API requires alternating roles, so merge them.
        if messages and messages[-1]["role"] == m.role:
            messages[-1]["content"].extend(content)
        else:
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
    return _salvage_chat_reply(text)
